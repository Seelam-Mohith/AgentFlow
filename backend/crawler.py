import asyncio
from collections import deque
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from backend.models import Page, CrawlOutput
from backend.security import SafeFetcher, validate_url


def extract(url: str, html: str) -> Page:
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.get_text(' ', strip=True)[:300] if soup.title else None
    meta = soup.find('meta', attrs={'name': 'description'})
    description = str(meta.get('content', ''))[:1000] if meta else None
    metadata = {str(tag.get('property') or tag.get('name')): str(tag.get('content'))[:500] for tag in soup.select('meta[content]')[:40] if tag.get('property') or tag.get('name')}
    links = []
    for tag in soup.select('a[href]'):
        try:
            link = validate_url(urljoin(url, str(tag['href'])))
            if link not in links:
                links.append(link)
        except ValueError:
            pass
        if len(links) >= 100:
            break
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript', 'form']):
        tag.decompose()
    main = soup.find('main') or soup.find('article') or soup.body or soup
    headings = [tag.get_text(' ', strip=True)[:300] for tag in main.select('h1,h2,h3')[:40]]
    paragraphs = [tag.get_text(' ', strip=True) for tag in main.select('p,li,td,blockquote')]
    content = '\n'.join(p for p in paragraphs if p) or main.get_text(' ', strip=True)
    return Page(url=url, title=title, description=description, headings=headings, content=content[:16000], links=links, metadata=metadata)


async def crawl(url: str, max_pages: int, emit=lambda message: None, fetcher=None) -> CrawlOutput:
    fetcher = fetcher or SafeFetcher()
    url = validate_url(url)
    origin = urlsplit(url)
    queue = deque([(url, 0)])
    seen, pages, errors, robots = set(), [], [], {}
    attempts = 0

    async def allowed(target):
        parts = urlsplit(target)
        base = f'{parts.scheme}://{parts.netloc}'
        if base not in robots:
            _, status, text, _ = await fetcher.get(base + '/robots.txt', limit=256000)
            if status in (401, 403) or status >= 500 or status == 429:
                raise ValueError(f'robots.txt unavailable or denies access (HTTP {status}); refusing crawl.')
            policy = RobotFileParser()
            policy.parse(text.splitlines() if status < 400 else [])
            robots[base] = policy
        policy = robots[base]
        delay = policy.crawl_delay('AgentFlowBot') or policy.crawl_delay('*') or 0
        if delay > 10:
            raise ValueError('robots.txt crawl delay exceeds the prototype time budget.')
        await asyncio.sleep(max(.3, delay))
        return policy.can_fetch('AgentFlowBot', target)

    while queue and attempts < max_pages:
        target, depth = queue.popleft()
        if target in seen:
            continue
        seen.add(target)
        attempts += 1
        try:
            if not await allowed(target):
                raise ValueError('Disallowed by robots.txt.')
            emit(f'Fetching {target}')
            async def check_redirect(destination):
                if urlsplit(destination).hostname != origin.hostname:
                    raise ValueError('Cross-domain page redirect refused.')
                if not await allowed(destination):
                    raise ValueError('Redirect destination disallowed by robots.txt.')
            final, status, html, kind = await fetcher.get(target, before_redirect=check_redirect)
            if status >= 400:
                raise ValueError(f'HTTP {status}')
            if 'text/html' not in kind.lower():
                raise ValueError('Response is not an HTML page.')
            if final in {page.url for page in pages}:
                continue
            page = extract(final, html)
            if not page.content.strip():
                raise ValueError('No useful content extracted.')
            pages.append(page)
            emit(f'Page extracted: {page.title or final}')
            if depth < 2:
                for link in page.links:
                    if urlsplit(link).hostname == origin.hostname and link not in seen:
                        if len(queue) < 200:
                            queue.append((link, depth + 1))
        except Exception as exc:
            error = f'{target}: {type(exc).__name__}: {exc}'[:600]
            errors.append(error)
            emit(error)
    return CrawlOutput(pages=pages, errors=errors, status='partial' if pages and errors else 'completed' if pages else 'failed')

