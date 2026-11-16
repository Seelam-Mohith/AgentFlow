# Verification record

Verified locally on November 16, 2026, using Windows, Python 3.12.5, Node.js 22.14.0, and Chromium through Playwright.

| Check | Actual result |
| --- | --- |
| Backend deterministic suite | 40 passed; live test skipped by default |
| Opt-in live API-to-CLI integration | 1 passed against https://example.com; actual public fetch, subprocess, JSON parsing, and grounded summary |
| Next.js production build | Passed on Next.js 16.4.6; route generation and TypeScript succeeded |
| TypeScript check | Passed (`tsc --noEmit`) |
| Browser full crawl / logs / JSON export | Passed against running local frontend and backend, with a real public crawler subprocess |
| Browser private-address rejection | Passed; failed task shown without fake results |
| Browser mobile welcome / settings | Passed at 390 × 844 |
| Browser mobile cancellation | Passed; cancel control returns a persisted cancelled task |
| Final browser suite | 4 passed in 13.1 seconds against the final production build |
| npm dependency audit | Zero known vulnerabilities after dependency upgrades |
| OpenAI key-backed mode | Not exercised; no key was configured for the demonstration |
| Docker Compose | Supplied but not executed; Docker unavailable in this environment |
| Video / public deployment | Not recorded / not deployed |

The deterministic suite exercises real subprocess output capture, nonzero exit code, timeout termination, cancellation termination, and output limits. HTTP fixtures cover robots denial, page limits, partial results, failed requests, and HTML extraction. Security tests cover unsafe URLs, mixed public/private DNS answers, IP pinning with original Host/SNI, unsafe redirects, and response size bounds. API tests cover schema validation, failed-task persistence, SSE delivery, unknown task IDs, and interrupted-task recovery.

The live integration and successful browser crawl were run with network access granted. Restricted sandbox execution cannot fetch public sites; that is an environment constraint, not a successful crawl. Initial dependency network failures and a temporary-directory restriction were resolved by granting the required execution access. Pytest emitted a non-fatal warning that its optional cache directory was not writable; tests themselves passed.

Screenshots are generated into ignored `frontend/test-results/` by browser tests. The database contains actual demonstration history, is ignored by version control, and is recreated automatically on a fresh checkout.
