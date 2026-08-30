<!-- capsule-v2 -->
# Playwright resilient helper toolkit — how do I build a tolerant Playwright helper layer that self-diagnoses selector failures, extracts text safely, closes modals, and waits for manual login?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c0e85bee8764d62565d229c682e5eb81bb` (linkedin_scraper twin is the same tree); Codebase Memory `joeyism-linkedin-scraper`. **Question:** what is the self-diagnosing wait/extract/cleanup helper set that keeps a Playwright scraper resilient to LinkedIn's changing DOM without brittle selectors?

## wait_for_element_smart + extract_text_safe + handle_modal_close + wait_for_manual_login
**Path/Symbol:** `linkedin_scraper/core/utils.py:wait_for_element_smart` (:108–142), `_get_selector_suggestions` (:145–151), `extract_text_safe` (:154–181), `handle_modal_close` (:245–271), `is_page_loaded` (:274–288); `linkedin_scraper/core/auth.py:wait_for_manual_login` (:282–314); exception taxonomy `core/exceptions.py` (`LinkedInScraperException` base, `ElementNotFoundError`, `AuthenticationError`, `RateLimitError` with `suggested_wait_time`).
**Signature:** `async wait_for_element_smart(page, selector, timeout=5000, state="visible", error_context=None) -> None` (raises `ElementNotFoundError` with suggestions); `async extract_text_safe(page, selector, default="", timeout=2000) -> str`; `async handle_modal_close(page) -> bool`; `async wait_for_manual_login(page, timeout=300000) -> None`.
**Data Shape:** every helper returns a safe default / bool instead of raising on transient misses — `extract_text_safe` returns `default` on timeout or any error; `handle_modal_close` returns True only if a dismiss/close button was found and clicked; `wait_for_manual_login` polls `is_logged_in` every 1 s until the timeout then raises `AuthenticationError`.

### Decisive source
```python
async def wait_for_element_smart(page, selector, timeout=5000, state="visible", error_context=None):
    try:
        await page.wait_for_selector(selector, timeout=timeout, state=state)
    except PlaywrightTimeoutError:
        context = f" when {error_context}" if error_context else ""
        suggestions = _get_selector_suggestions(selector)   # #id → "dynamic"; pv-/artdeco → "changes frequently"
        raise ElementNotFoundError(
            f"Could not find element with selector '{selector}'{context}. "
            f"This may indicate:\n  • The page structure has changed\n  • The profile has restricted visibility\n"
            f"  • The content doesn't exist on this page\n  • Network slowness (try increasing timeout)\n{suggestions}")

def _get_selector_suggestions(selector):
    if '#' in selector: return "Tip: ID selectors may be dynamic. Consider using data attributes or text content."
    elif 'pv-' in selector or 'artdeco' in selector:
        return "Tip: LinkedIn class names change frequently. This selector may need updating."
    return ""

async def extract_text_safe(page, selector, default="", timeout=2000):
    try:
        element = page.locator(selector).first
        text = await element.text_content(timeout=timeout)
        return text.strip() if text else default
    except (PlaywrightTimeoutError, Exception):
        return default                                    # never raise on a missing element

async def handle_modal_close(page):
    close_button = page.locator(
        'button[aria-label="Dismiss"], button[aria-label="Close"], button.artdeco-modal__dismiss').first
    if await close_button.is_visible(timeout=1000):
        await close_button.click(); await asyncio.sleep(0.5); return True
    return False
```

**Flow:** a wait that must succeed → `wait_for_element_smart` (raises a *self-diagnosing* `ElementNotFoundError` that lists likely causes + selector-type tips); a wait that may be absent → `extract_text_safe` (returns a default) or `handle_modal_close` (best-effort dismiss of any `Dismiss`/`Close`/`artdeco-modal__dismiss` button); a long interactive step → `wait_for_manual_login` polls `is_logged_in` every 1 s for up to 5 min (2FA/CAPTCHA) then raises `AuthenticationError`. All transient failures are swallowed per-helper so a flaky read can't crash the run.
**Invariant:** the split is by *failure severity*: hard-required elements raise with actionable diagnostics (`ElementNotFoundError`), optional elements degrade to safe defaults/bools. The `RateLimitError` carries a `suggested_wait_time` payload (see rate-limit-detection.md) and the whole taxonomy derives from one `LinkedInScraperException` base so callers can catch broadly. `extract_text_safe` strips whitespace and never raises — a porter who lets it raise breaks the "optional element" contract.
**Probe:** `tests/test_auth.py::test_is_logged_in_false` (:7–14) pins the negative auth path via `BrowserManager`; the resilient helpers have no direct unit tests — coverage caveat recorded; behavior verified by reading core/utils.py + core/auth.py at HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "wait_for_element_smart", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "handle_modal_close", limit: 10 });
```

## Verdict
Adopt the severity-split helper set (self-diagnosing hard wait vs safe-default optional extract/close), the selector-tip generator, and the poll-based manual-login wait; adapt the dismiss-button selectors and the tip heuristics (rot against live LinkedIn); omit the emoji logging and the proceed-anyway policy if your host needs strict guarantees. Probe caveat: only the auth negative path is test-pinned; the helper toolkit is source-grounded.
