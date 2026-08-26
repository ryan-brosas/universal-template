<!-- capsule-v2 -->
# Scraper base class & progress callbacks — how do I compose navigation, guards, and extraction into testable scraper objects with observable progress?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c0e85bee8764d62565d229c682e5eb81bb` (`scrapers/base.py` 269L, `callbacks.py` 162L). Codebase Memory `joeyism-linkedin-scraper`. **Question:** what base-class method set and callback protocol let concrete scrapers stay thin while every run reports progress to console/JSON/multi sinks?

## BaseScraper + ProgressCallback protocol
**Path/Symbol:** `linkedin_scraper/scrapers/base.py:BaseScraper` (:24–269 — guard methods :38–57, navigation :156–168, extraction helpers :107–252); `linkedin_scraper/callbacks.py:ProgressCallback` (:8–48) with ConsoleCallback (:51–81), SilentCallback (:84–86), JSONLogCallback (:89–129), MultiCallback (:132–162).
**Signature:** `BaseScraper(page, callback=None)` (defaults Silent); hooks: `ensure_logged_in()`, `check_rate_limit()`, `navigate_and_wait(url, wait_until='domcontentloaded', timeout=60000)`, `safe_extract_text(selector, default, timeout)`, `get_attribute_safe(...)`, `extract_list_items(container, item, timeout)`, `safe_click` (decorated `@retry_async(max_attempts=3, backoff=2.0)`); protocol: `on_start(scraper_type,url)`, `on_progress(message, percent)`, `on_complete(type,result)`, `on_error(error)` — all async.
**Data Shape:** progress = `(message:str, percent:0-100)`; JSON sink appends `{timestamp, event_type, **data}` lines; MultiCallback fans out in registration order.

### Decisive source
```python
async def navigate_and_wait(self, url, wait_until='domcontentloaded', timeout=60000):
    await self.page.goto(url, wait_until=wait_until, timeout=timeout)
    await self.check_rate_limit()          # EVERY navigation ends with the throttle guard

@retry_async(max_attempts=3, backoff=2.0, exceptions=(PlaywrightTimeoutError,))
async def safe_click(self, selector, timeout=5000) -> bool: ...   # only timeouts retry

# silent-by-default composition:
def __init__(self, page, callback=None):
    self.callback = callback or SilentCallback()
```

**Flow:** concrete scraper (e.g. JobSearchScraper.search) emits on_start → navigate_and_wait (goto + rate check) → on_progress at each phase (20/50/90) → extract via safe_* helpers → on_complete; any exception → on_error; UI-free tests inject SilentCallback.
**Invariant:** rate-limit check is fused into navigation (impossible to forget); only timeout-class exceptions are retryable (see rate-limit-detection.md); callbacks default to Silent so library code never prints unless handed a sink; extraction helpers ALWAYS return defaults ([]/""), never raise, so one missing element can't kill a batch.
**Probe:** `tests/test_job_scraper.py::test_job_search_scraper` + `tests/test_person_scraper.py::test_person_scraper_basic` exercise BaseScraper composition end-to-end behind the session fixture; model round-trips unit-tested without network.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "BaseScraper", limit: 5 });
```

## Verdict
Adopt guard-fused navigation, default-silent async callback protocol, and default-returning extraction helpers; adapt the phase percentages and sink formats to host; omit the bring_to_front focus hack if headless. Probe caveat: integration tests need a live session file; contract logic itself runs network-free.
