<!-- capsule-v2 -->
# Async retry decorator + the swallow-that-disarms-it trap — how do I add opt-in exponential-backoff retry to async scraping calls without a swallowed-exception body silently disarming it?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c0e85bee8764d62565d229c682e5eb81bb`; Codebase Memory `joeyism-linkedin-scraper`. **Question:** how do I add opt-in exception-tuple retry with exponential backoff to async scrape calls, and why can its one in-repo usage never actually retry?

## Opt-in exception-tuple retry kernel
**Path/Symbol:** `linkedin_scraper/core/utils.py:retry_async` (:14–56 file, graph :16–54); applied at `scrapers/base.py:BaseScraper.safe_click` (:122–142 graph / :131 decorated).
**Signature:** `retry_async(max_attempts: int = 3, backoff: float = 2.0, exceptions: tuple = (Exception,))` → decorator over `async def (*args, **kwargs)`.
**Data Shape:** config-only decorator; retries when the wrapped call RAISES an instance of `exceptions`; sleeps `backoff ** attempt` between attempts (0s, then backoff, backoff²…); after the last attempt logs "All N attempts failed" and re-raises `last_exception`. Non-matching exceptions propagate immediately.

### Decisive source
```python
# utils.py — the kernel: only RAISED tuple-members retry
for attempt in range(max_attempts):
    try:
        return await func(*args, **kwargs)
    except exceptions as e:
        last_exception = e
        if attempt < max_attempts - 1:
            wait_time = backoff ** attempt
            await asyncio.sleep(wait_time)
        else:
            logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
raise last_exception

# base.py — the trap: the ONLY decorated call swallows the exact tuple member
@retry_async(max_attempts=3, backoff=2.0, exceptions=(PlaywrightTimeoutError,))
async def safe_click(self, selector: str, timeout: float = 5000) -> bool:
    try:
        await self.page.locator(selector).first.click(timeout=timeout)
        return True
    except PlaywrightTimeoutError:
        return False          # <- raised timeout never reaches the decorator
```

**Flow:** call → wrapper loop → raise? ∈ tuple → sleep backoff^attempt → retry … exhausted ⇒ log + raise LAST exception. In safe_click's case: click raises PlaywrightTimeoutError → inner except returns False → wrapper sees a normal False return on attempt 1 of 1.
**Invariant:** the decorator observes only exceptions that LEAVE the wrapped function; any body that catches its own `exceptions` members (or bare `except`) converts retries into single silent sentinel returns. If you decorate, the body must let tuple members propagate (catch only what you will NOT retry).
**Probe:** live headless run against the repo's own BrowserManager: `await BaseScraper(page).safe_click('button[data-does-not-exist="x"]', timeout=1000)` → `False in 1.00s` (single attempt; an armed ladder would spend ~1s+2s sleeping). Structural: `inspect.getsource(BaseScraper.safe_click)` contains both `@retry_async` and `return False` under `except PlaywrightTimeoutError:`. No direct unit test pins retry_async itself — coverage caveat: probe is behavioral+structural at HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "retry_async", limit: 6 });
// → linkedin_scraper.core.utils.retry_async Function utils.py :16–54
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "safe_click", limit: 6 });
// → BaseScraper.safe_click Method base.py :122–142
```

## Verdict
Adopt the decorator shape (config-at-decoration-time, tuple-scoped retry, last-exception re-raise) for flaky network boundaries. Adapt backoff base/attempts per host SLA; log per attempt. Omit joeyism's safe_click pairing unless you remove its inner catch — porting both verbatim ships a retry that never fires. Coverage caveat: no direct test pins the decorator; claims are source+live-behavior probes at the pinned HEAD.
