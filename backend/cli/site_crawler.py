import argparse
import asyncio
import sys
from backend.config import MAX_PAGES
from backend.crawler import crawl
from backend.security import validate_url


def main():
    parser = argparse.ArgumentParser(description='AgentFlow public website crawler')
    parser.add_argument('--url', required=True, type=validate_url)
    parser.add_argument('--max-pages', type=int, choices=range(1, MAX_PAGES + 1), default=MAX_PAGES)
    parser.add_argument('--output', choices=['json'], default='json')
    args = parser.parse_args()
    output = asyncio.run(crawl(args.url, args.max_pages, lambda message: print(message, file=sys.stderr, flush=True)))
    print(output.model_dump_json())
    return 1 if output.status == 'failed' else 0


if __name__ == '__main__':
    sys.exit(main())

