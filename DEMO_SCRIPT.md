# AgentFlow: 4-minute demonstration

## Before recording

Install dependencies; start the backend and frontend using README instructions. Check `/api/health`. Ensure public HTTPS access to example.com. Use a clean new conversation. Keep API keys and `.env` out of frame. This document is a recording script; no video has been recorded as part of the implementation.

## 0:00–0:30 — Problem and introduction

“A simple request like ‘analyze this website’ often means opening a terminal, choosing tools, extracting text, and reformatting results. AgentFlow turns that workflow into a conversation while keeping execution visible.”

Show the dark chat workspace, prompt cards, and approved crawler panel.

## 0:30–1:00 — Architecture

Show the README Mermaid diagram. Explain: Next.js sends a request to FastAPI; a validated intent selects one approved Python worker; asyncio launches a real subprocess; HTTPX and BeautifulSoup collect website content; Pydantic validates stdout JSON; the backend summarizes and persists the result. SSE supplies progress.

“With an API key, OpenAI interprets the intent and summarizes the content. Without a key, the same real crawler works with deterministic parsing and an extractive summary.”

## 1:00–2:00 — Live prompt and real execution

Enter:

> Crawl https://example.com, extract important information, give me a summary, and return JSON.

Show the stages advancing. Point out URL validation, selected CLI, running crawler, extraction, and summary. Do not claim a successful crawl until the task actually completes.

Open Execution logs. Highlight `python -m backend.cli.site_crawler --url https://example.com/ --max-pages 5 --output json`, actual stderr diagnostics, captured stdout, exit code, and elapsed time.

## 2:00–2:45 — Results and transparency

Show “Example Domain” and its summary. Open Pages to inspect the fetched URL, title, headings, and content. Open JSON, expand the result and execution objects, switch to source, and export the record. Reopen the task from history.

“These values came from the public website and the actual process. A page is only counted after a successful fetch and extraction.”

## 2:45–3:30 — Failure and cancellation

Start a new conversation with `Crawl http://127.0.0.1 and summarize it.` Show the blocked private address and visible failed state. There must be no invented success result.

For cancellation, start `Crawl https://example.com 5 pages and summarize the website.` Click Cancel immediately while it is running. If it finishes too quickly, explain that cancellation is covered by an automated real-subprocess test rather than claiming to have demonstrated it live.

## 3:30–4:00 — Security and closing

Show the approved tool allowlist and pinned HTTP request implementation. Explain validated arguments, no shell commands, public DNS/IP checks on redirects, robots restrictions, bounded execution/output, and real process termination. Mention that page content is untrusted and cannot issue commands.

“AgentFlow is a working local prototype with inspectable execution. Next steps are authenticated workspaces, isolated workers, and more approved tools.” Show test results from `VERIFICATION.md`, distinguishing actual checks from tests needing credentials or infrastructure.
