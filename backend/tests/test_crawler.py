import pytest
from backend.crawler import crawl, extract

HTML = '<html><head><title>Real fixture</title><meta name="description" content="Test description"></head><body><nav>Discard me</nav><main><h1>Heading</h1><p>Useful content from the site.</p><a href="/second">Second</a><a href="/missing">Missing</a></main><script>evil()</script></body></html>'


class Fetcher:
    def __init__(self, robots='', failures=False):
        self.robots, self.failures, self.calls = robots, failures, []

    async def get(self, url, limit=None, before_redirect=None):
        self.calls.append(url)
        if url.endswith('robots.txt'):
            return url, 200, self.robots, 'text/plain'
        if self.failures and url.endswith('/second'):
            return url, 500, '', 'text/html'
        if url.endswith('/missing'):
            return url, 404, '', 'text/html'
        return url, 200, HTML, 'text/html'


def test_html_extraction():
    page = extract('https://example.com/', HTML)
    assert page.title == 'Real fixture'
    assert page.description == 'Test description'
    assert page.headings == ['Heading']
    assert 'Discard me' not in page.content and 'evil()' not in page.content
    assert page.links[0] == 'https://example.com/second'


async def test_page_limits():
    fetcher = Fetcher()
    output = await crawl('https://example.com', 1, fetcher=fetcher)
    assert len(output.pages) == 1
    assert len(fetcher.calls) == 2
    assert output.status == 'completed'


async def test_robots_denial():
    fetcher = Fetcher('User-agent: *\nDisallow: /')
    output = await crawl('https://example.com', 2, fetcher=fetcher)
    assert output.status == 'failed'
    assert not output.pages
    assert 'robots.txt' in output.errors[0]
    assert len(fetcher.calls) == 1


async def test_partial_http_failure():
    output = await crawl('https://example.com', 3, fetcher=Fetcher(failures=True))
    assert output.status == 'partial'
    assert len(output.pages) == 1
    assert any('HTTP 500' in e for e in output.errors)
    assert any('HTTP 404' in e for e in output.errors)


async def test_unreachable():
    class Unreachable:
        async def get(self, *a, **kw): raise OSError('Network unavailable')
    output = await crawl('https://example.com', 1, fetcher=Unreachable())
    assert output.status == 'failed'
    assert 'Network unavailable' in output.errors[0]
