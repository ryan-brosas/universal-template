<!-- capsule-v2 -->
# Feed-auth proxy triage — when is a failed auth probe a proxy fault instead of a dead session?

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb`; Codebase Memory `linkedin-mcp-server`. **Question:** How should a session validator classify failures so a broken proxy never retires a valid login?

## Barrier evidence outranks proxy explanation, which outranks failure
**Path/Symbol:** `linkedin_mcp_server/drivers/browser.py:_feed_auth_succeeds` (:182), `_log_feed_failure_context` (:142); helpers from core: `raise_if_proxy_error`, `raise_if_proxy_configured`, `detect_auth_barrier_quick`, `resolve_remember_me_prompt`.
**Signature:** `async def _feed_auth_succeeds(browser, *, allow_remember_me: bool = True) -> bool` — raises (proxy errors) rather than returning False when the session is unproven.
**Data Shape:** Success = `/feed/` loads `domcontentloaded`, optional remember-me resolution, then `detect_auth_barrier_quick(page)` returns None. The quick check reads ONLY URL + title (cheap enough to run after every navigation); the full variant adds a body-text marker scan.

### Decisive source
```text
except Exception as exc:
    raise_if_proxy_error(exc)        # FIRST, before anything else: a proxy
                                     # fault is not a dead session; returning
                                     # False would retire a valid profile and
                                     # tell the user to re-login, which cannot
                                     # fix an unreachable proxy.
    if allow_remember_me and await resolve_remember_me_prompt(page):
        return await _feed_auth_succeeds(browser, allow_remember_me=False)
    barrier = await detect_auth_barrier_quick(browser.page)
    # A failed navigation STILL leaves URL+title behind — real session evidence,
    # and it must OUTRANK the proxy explanation below.
    ...
    if barrier is None:
        # Nothing loaded and no barrier ⇒ nothing proves the session dead; with
        # a proxy in front the likeliest cause IS the proxy. Wrong credentials
        # in particular produce NO proxy error code at all: Chromium retries the
        # 407 challenge until the navigation TIMES OUT (verified against a local
        # authenticating relay), so no marker check can catch it.
        raise_if_proxy_configured(exc)   # raises only when a proxy is configured
    return False

Logging discipline: reason strings pass redact_proxy_credentials(); the
exception is deliberately NOT logged with exc_info anywhere — driver errors can
quote the proxy URL, and these lines/traces are what users paste into issues.
```

**Flow:** goto /feed/ → stabilize → remember-me resolution (recursive retry once, flag-guarded against loops) → quick barrier check → barrier? log context + False : True. On exception: proxy-error re-raise → remember-me recovery retry → barrier-from-partial-evidence check → proxy-configured re-raise → False only when LinkedIn itself proved the session dead.
**Invariant:** Classification order is load-bearing: (1) hard proxy error → raise; (2) any page-committed barrier evidence → session verdict; (3) nothing loaded + proxy configured → raise; (4) nothing loaded + direct connection → False. Reordering any two steps either destroys valid sessions or hides proxy faults behind re-login advice that cannot work.
**Probe:** `grep -c 'raise_if_proxy_configured(exc)' linkedin_mcp_server/drivers/browser.py` → 1; `grep -c 'detect_auth_barrier_quick(browser.page)' linkedin_mcp_server/drivers/browser.py` → 2; direct tests: `tests/test_browser_driver.py::test_feed_auth_retries_feed_after_remember_me_error_recovery` (:189), `test_feed_auth_records_single_post_recovery_trace` (:214).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "_feed_auth_succeeds raise_if_proxy_configured auth barrier", limit: 5 });
```

## Verdict
Adopt the four-way classification ladder for any remote-session validator fronted by an optional egress proxy. Adapt marker detection to your target's DOM. Omit remember-me specifics (LinkedIn UI artifact).
