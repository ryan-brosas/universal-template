<!-- capsule-v2 -->
# Manual-login session producer — how do I turn one human login into a durable session artifact that every headless tool and test can key on?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c0e85b…`; Codebase Memory `joeyism-linkedin-scraper`. **Question:** what is the minimal machine-assisted flow that converts an interactive (2FA/CAPTCHA) login into a reusable session file, with honest failure at both ends?

## Poll is_logged_in until human finishes, then persist
**Path/Symbol:** `samples/create_session.py:create_session` (:20–75) + `linkedin_scraper/core/auth.py:wait_for_manual_login` (:282–314); persistence via `core/browser.py:BrowserManager.save_session` (:163).
**Signature:** `async def wait_for_manual_login(page: Page, timeout: int = 300000) -> None`; producer wraps it in `async with BrowserManager(headless=False)`.
**Data Shape:** no inputs beyond the page; output = linkedin_session.json at repo root (Playwright storage_state). Raises AuthenticationError on timeout; returns silently the moment the shared predicate flips true.

### Decisive source
```python
while True:
    if await is_logged_in(page):          # 1s poll loop, no fixed total sleep
        return
    elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
    if elapsed > timeout:
        raise AuthenticationError("Manual login timeout. ...")
    await asyncio.sleep(1)
# producer side: headed browser + generous budget + immediate persistence
async with BrowserManager(headless=False) as browser:
    await browser.page.goto("https://www.linkedin.com/login")
    await wait_for_manual_login(browser.page, timeout=300000)   # 5 min for 2FA/CAPTCHA
    await browser.save_session("linkedin_session.json")
```

**Flow:** open HEADLESS=False (LinkedIn blocks headless) → navigate to /login → print step list for the human → poll `is_logged_in` every 1s up to timeout → success ⇒ save_session immediately; timeout ⇒ typed AuthenticationError, producer prints remediation and exits non-success.
**Invariant:** completion detection must reuse the SAME `is_logged_in` predicate consumers use (URL-blocklist fail-fast → nav-selector count → authenticated-URL fallback) so "produced a session" and "session works" can never diverge; the artifact is written only after observed login, never speculatively. Session files contain auth cookies — gitignored by design.
**Probe:** interactive login is human-gated — execution blocked BY DESIGN in this environment (no credentials; recorded as runner block, not skipped silently). Structural probes executed: grep pins `wait_for_manual_login` at core/auth.py:282 and `save_session` at core/browser.py:163; downstream consumption proven live by the skip-gate probe in integration-skip-gate-markers (tests skip loudly exactly when this file is absent).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "browser_with_session", limit: 5 });
// → tests.conftest.browser_with_session Function conftest.py :40–53 (the consumer gate)
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "login_with_credentials", limit: 10 });
// → auth family incl. wait_for_manual_login (:282–314)
```

## Verdict
Adopt the headed-browser + predicate-polling producer for any scraper whose target requires interactive auth; the 1s poll with deadline beats fixed sleeps because it completes the instant login lands. Adapt timeout budgets (300s here) and the saved artifact path. Omit LinkedIn-specific URLs/predicates; port your own is_logged_in equivalent but keep ONE predicate shared by producer, verifier, and tests. Caveat: end-to-end run needs a human; evidence here is source-pinned plus consumer-side behavioral proof.
