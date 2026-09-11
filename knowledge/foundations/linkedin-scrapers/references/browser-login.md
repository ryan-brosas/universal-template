<!-- capsule-v2 -->
# Browser login ladder — how do I automate LinkedIn login with a real browser and know which failure state I hit?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c0e85bee8764d62565d229c682e5eb81bb` (linkedin_scraper twin is the same tree); Codebase Memory `joeyism-linkedin-scraper`. **Question:** what post-login URL states must a porter distinguish, and how is success verified when selectors churn?

## login_with_credentials / login_with_cookie / is_logged_in
**Path/Symbol:** `linkedin_scraper/core/auth.py:login_with_credentials` (:65–188), `warm_up_browser` (:17–44), `login_with_cookie` (:191–242), `is_logged_in` (:245–279).
**Signature:** `async login_with_credentials(page, email=None, password=None, timeout=30000, warm_up=True)`; `async is_logged_in(page) -> bool`; creds fall back to `.env` (`LINKEDIN_EMAIL|LINKEDIN_USERNAME`, `LINKEDIN_PASSWORD`) via `load_credentials_from_env`.
**Data Shape:** outcome space after submit = feed (success) / checkpoint|challenge (security hold) / authwall (bot wall) / still-on-login (bad credentials). Cookie path injects `{name:"li_at", domain:".linkedin.com", path:"/"}` then verifies by landing on `/feed/`.

### Decisive source
```python
await page.wait_for_url(
    lambda url: 'feed' in url or 'checkpoint' in url or 'authwall' in url,  # ALL three are "navigated"
    timeout=timeout)
...
if 'checkpoint' in current_url or 'challenge' in current_url:
    raise AuthenticationError("LinkedIn security checkpoint detected. ...")   # distinct error class per state
if 'authwall' in current_url:
    raise AuthenticationError("Authentication wall encountered. ...")

# is_logged_in: fail-fast blockers → selector check (old+new nav) → URL fallback
auth_blockers = ['/login', '/authwall', '/checkpoint', '/challenge', '/uas/login', '/uas/consumer-email-challenge']
has_nav_elements = old_count > 0 or new_count > 0     # '.global-nav__primary-link...' OR 'nav a[href*="/feed"]...'
return has_nav_elements or is_authenticated_page
```

**Flow:** optional warm-up (google→wikipedia→github, 1 s pauses, best-effort) → `/login` → rate-limit pre-check → fill #username/#password → submit → wait for ANY known destination → classify checkpoint/authwall/still-login into distinct errors → verify by polling `is_logged_in()` every 0.5 s for ≤5 s; verification timeout logs a warning and PROCEEDS (never hard-fails on flaky nav detection).
**Invariant:** never trust one signal — URL classification, dual-generation nav selectors, and authenticated-page fallback must all agree paths; every failure raises `AuthenticationError` with the current URL embedded so callers can react per state.
**Probe:** `tests/test_auth.py::test_is_logged_in_false` (:7–14) — fresh context must return bool False-ish without session (integration variant `test_is_logged_in_with_session` :17–25 skips unless `linkedin_session.json` exists).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "login_with_credentials", limit: 10 });
// also resolves warm_up_browser, is_logged_in, load_credentials_from_env + direct test node test_is_logged_in_false
```

## Verdict
Adopt the three-destination wait + per-state error taxonomy and the layered is_logged_in ladder; adapt warm-up site list, env-var names, and selector generations to host (they rot); omit the emoji logging and the proceed-anyway policy if your host needs strict guarantees. Probe caveat: non-integration test only covers the negative path.
