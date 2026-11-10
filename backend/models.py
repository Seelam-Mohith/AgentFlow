from typing import Literal
from pydantic import BaseModel, Field, ConfigDict
from backend.config import MAX_PAGES


class Intent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    task_type: Literal['website_crawl'] = 'website_crawl'
    url: str = Field(min_length=1, max_length=2048)
    operations: list[Literal['crawl', 'extract', 'summarize']] = ['crawl', 'extract', 'summarize']
    output_format: Literal['both', 'json', 'summary'] = 'both'
    max_pages: int = Field(default=MAX_PAGES, ge=1, le=MAX_PAGES)
    instructions: str = Field(default='', max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class Page(BaseModel):
    url: str
    title: str | None
    description: str | None
    headings: list[str]
    content: str
    links: list[str]
    metadata: dict[str, str]
    status: Literal['completed'] = 'completed'


class CrawlOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    pages: list[Page] = Field(max_length=10)
    errors: list[str]
    status: Literal['completed', 'partial', 'failed']


class Finding(BaseModel):
    text: str
    source_url: str


class Summary(BaseModel):
    summary: str
    key_findings: list[Finding]


class TaskResult(Summary):
    website_url: str
    website_title: str | None
    description: str | None
    pages: list[Page]
    total_pages_crawled: int = Field(ge=1, le=10)
    source_urls: list[str]


class ProgressEvent(BaseModel):
    id: int
    stage: int = Field(ge=0, le=7)
    message: str
    time: str


class ExecutionRecord(BaseModel):
    tool: Literal['site_crawler']
    command: list[str]
    started_at: str | None
    exit_code: int | None
    duration_seconds: float
    stdout: str
    stderr: str
    errors: list[str]
    intent_mode: str | None
    summary_mode: str | None


class TaskRecord(BaseModel):
    task_id: str
    task_type: Literal['website_crawl']
    message: str
    status: Literal['queued', 'running', 'completed', 'partial', 'failed', 'cancelled']
    created_at: str
    stage: int = Field(ge=0, le=7)
    input: Intent | None
    result: TaskResult | None
    events: list[ProgressEvent]
    execution: ExecutionRecord

