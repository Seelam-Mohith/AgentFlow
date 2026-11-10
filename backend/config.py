import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
MAX_PAGES = min(10, max(1, int(os.getenv('MAX_CRAWL_PAGES', '5'))))
TIMEOUT = min(180, max(1, float(os.getenv('CRAWL_TIMEOUT_SECONDS', '60'))))
DATABASE = os.getenv('DATABASE_URL', 'sqlite:///./agentflow.db').removeprefix('sqlite:///')

