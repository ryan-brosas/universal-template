<!-- capsule-v2 -->
# Session-verdict evidence tiers — when a session verifier can neither prove login nor prove logout, should the run die or proceed?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c0e85bee8764d62565d229c682e5eb81bb`; Codebase Memory `joeyism-linkedin-scraper`. **Question:** a post-authentication check can end three ways — observed death, confirmed life, or *inconclusive*. What should each outcome do, and where does the decision belong?

## Three-tier verdict inside login_with_cookie
**Path/Symbol:** `linkedin_scraper/core/auth.py:login_with_cookie` (:191–242 — negative tier :216–219, poll tier :228–241, wrap-all except :240–242); predicate `is_logged_in` (:245–279, shared with wait_for_manual_login/login_with_credentials — see session-producer-manual-login-poll); counter-policy `core/browser.py:BrowserManager.load_session` (:183–213, sets `_is_authenticated = True` at :211).
**Signature:** `async def login_with_cookie(page: Page, cookie_value: str) -> None` — one raw `li_at` string; planted via `page.context.add_cookies` into the RUNNING context (`domain: '.linkedin.com'`, `path: '/'` hardcoded); raises only `AuthenticationError`.
**Data Shape:** input = single cookie value (no file, no jar); outcomes = silent return (verified OR unverifiable-but-proceeded), or one typed `AuthenticationError` regardless of underlying cause.

### Decisive source
```python
# TIER 1 — NEGATIVE evidence: observed death ⇒ fail closed, typed raise
await page.goto('https://www.linkedin.com/feed/', wait_until='domcontentloaded')
if 'login' in page.url or 'authwall' in page.url:
    raise AuthenticationError(
        "Cookie authentication failed. The cookie may be expired or invalid.")

# TIER 2 — ABSENT evidence: poll the shared predicate 0.5s×10; inconclusive ⇒ loud proceed
while (time.time() - start_time) * 1000 < 5000:
    if await is_logged_in(page):
        logger.info("✓ Successfully authenticated with cookie")
        logged_in = True
        break
    await asyncio.sleep(0.5)
if not logged_in:
    logger.warning(
        "Could not verify cookie login. "
        "Proceeding anyway...")                    # returns normally!

# TIER 3 — everything else collapses into the SAME typed error
except Exception as e:
    if isinstance(e, AuthenticationError):
        raise                                      # typed passthrough — never double-wraps
    raise AuthenticationError(f"Cookie authentication error: {e}")
```

**Flow:** plant `li_at` → goto `/feed` → TIER 1 asks "did LinkedIn SAY we're dead?" (redirected to `login`/`authwall`) — yes ⇒ typed raise, no run continues on known-dead cookies → TIER 2 asks "can we CONFIRM life?" — poll `is_logged_in` every 0.5 s for ≤5 s; confirmation logs success and returns; budget exhausted logs the loud `"Could not verify cookie login. Proceeding anyway..."` and STILL RETURNS NORMALLY → TIER 3 catches everything else: an already-typed `AuthenticationError` passes through untouched; any other cause (navigation crash, context gone) is wrapped so callers catch exactly one type. The predicate itself carries old+new nav-selector generations because A/B-tested DOM made it report false negatives (issue #269; `samples/scrape_login.py` is the validation harness).
**Invariant:** the verdict branches on EVIDENCE TYPE, never on optimism: negative evidence fails closed; absent evidence fails OPEN but deposits a loud warning so downstream failures stay attributable; untyped causes never escape with their original type. The same repo holds the opposite trust policy one layer down — `BrowserManager.load_session` swaps the context around a storage_state file and sets `_is_authenticated = True` BY CONSTRUCTION (a write-only flag: zero readers anywhere in the tree). Artifact-trust bookkeeping and demanded-evidence verification coexist deliberately; a porter must choose per call site which policy a flag's consumers may assume.
**Probe:** executed at pinned HEAD (structural, offline): `inspect.getsource(login_with_cookie)` contains both `'authwall' in page.url` (tier 1) and `'Proceeding anyway...'` (tier 2), plus the `isinstance(e, AuthenticationError)` passthrough (tier 3); repo unit lane green as regression (`pytest -m unit` → 7 passed / 15 deselected). Live redirect/poll outcomes need real LinkedIn — blocked by design offline (same recorded block as the credentials path in browser-login.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "login_with_cookie", limit: 10 });
// → Function core/auth.py :191–242 (callers_total 0: consumer-facing API, samples use the credentials path)
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "load_session is_authenticated", limit: 10 });
// → Method core/browser.py :183–213 + write-only property pair :236–244
```

## Verdict
Adopt the three-way verdict (observed-death ⇒ typed throw; unverifiable ⇒ loud-warning proceed; other-causes ⇒ wrap into the one type callers already catch) for ANY post-auth or post-restore check whose probe can be inconclusive; adopt the typed-passthrough guard so wrapping never double-wraps. Adapt poll budget to surface risk (5 s here for a cookie you could still abandon; the manual-login producer budgets 300 s because a human is mid-loop) and cookie domain/path to host. Choose explicitly between this evidence-demanding policy and artifact-trust restoration (`browser-lifecycle.md` owns load_session mechanics): never let a by-construction flag masquerade as verified state. Omit the hardcoded `.linkedin.com` and the emoji log lines. Position among siblings: `cookie-session-bootstrap` (linkedin-profile-scraper-api) is the BINARY decisive probe — use it when one navigation always decides; `browser-login.md` owns the credentials ladder including its own post-submit proceed-on-timeout clause — this capsule generalizes that clause into the tier rule and adds the wrap-all contract. Coverage caveat: tiers 1–2 semantics are live-site behavior; evidence here is whole-function source read at the pinned HEAD plus executed structural probes and the unit-lane regression.
