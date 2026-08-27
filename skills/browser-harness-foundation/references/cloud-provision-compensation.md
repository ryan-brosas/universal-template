<!-- capsule-v2 -->
# Cloud-browser provisioning compensation — how do you provision a billed resource without leaking it when startup fails, and what happens when BOTH the start AND the cleanup fail?

**Source:** browser-harness MIT `main@6bb1c847fd62638554618e8d1e03247b935ff9cf`; Codebase Memory `browser-harness`. **Question:** What is the create→attach→compensate contract for remote browser sessions — including cleanup retries, twin-failure reporting, and display side effects that must be suppressible before anything billable exists?

## Create-BEFORE-attach with BaseException-wide retried undo + twin-failure group
**Path/Symbol:** `src/browser_harness/admin.py`: `start_remote_daemon` (:701-740; compensation :724-737), `_stop_cloud_browser(browser_id, strict=False)` (:601-615), `_should_show_remote_live_view` (:648-658) evaluated pre-provisioning (:716), `_resolve_profile_name` (:691-698).
**Signature:** `start_remote_daemon(name="remote", profileName=None, **create_kwargs) -> dict`; `_stop_cloud_browser(browser_id, strict=False) -> bool`; `_should_show_remote_live_view() -> bool`.
**Data Shape:** `POST /browsers` returns `{id, cdpUrl, liveUrl, ...}`; daemon env gets `BU_CDP_WS` (resolved from cdpUrl via `/json/version`) + `BU_BROWSER_ID`; cleanup failure after start failure raises `BaseExceptionGroup("remote daemon startup and cloud browser cleanup both failed", [start_error, cleanup_error])`.

### Decisive source
```python
    browser = _browser_use("/browsers", "POST", create_kwargs)
    try:
        ensure_daemon(
            name=name,
            env={"BU_CDP_WS": _cdp_ws_from_url(browser["cdpUrl"]), "BU_BROWSER_ID": browser["id"]},
        )
    except BaseException as start_error:
        try:
            _stop_cloud_browser(browser.get("id"), strict=True)
        except BaseException as cleanup_error:
            raise BaseExceptionGroup(
                "remote daemon startup and cloud browser cleanup both failed",
                [start_error, cleanup_error],
            )
        raise
```
with the retried undo itself:
```python
def _stop_cloud_browser(browser_id, strict=False):
    if not browser_id:
        return True
    last_error = None
    for attempt in range(3):
        try:
            _browser_use(f"/browsers/{browser_id}", "PATCH", {"action": "stop"})
            return True
        except BaseException as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))
    if strict:
        raise RuntimeError(f"failed to stop remote browser {browser_id}: {last_error}")
    return False
```

**Flow:** evaluate `BH_OPEN_LIVE_URL` FIRST (:716 — a bad value fails before any billable browser exists) → refuse if daemon already alive → profileName resolved client-side via paginated listing (0 or >1 exact-name matches ⇒ loud RuntimeError suggesting profileId) → POST create → ensure_daemon(env) → on failure PATCH-stop up to 3 attempts (`0.5*(attempt+1)` backoff, BaseException-wide so Ctrl-C still bills-off); if the stop ALSO fails, both errors travel in a named BaseExceptionGroup — never swallow the start error, never skip billing cleanup silently; success never stops the browser. Display side effects (`print` + open live URL) are gated by the suppression flag while the returned `liveUrl` stays intact.
**Invariant:** The compensation catch must be `BaseException` — Ctrl-C between create and attach would otherwise orphan a BILLED cloud browser; strict cleanup re-raises so twin failures compose instead of masking; success path issues exactly one POST; ambiguous profile names refuse to guess. `BH_OPEN_LIVE_URL` accepts {1,true,yes,on}/{0,false,no,off} case-insensitively and raises ValueError on anything else — fail-loud beats fail-default for an operator typo.

**Probe:** `tests/unit/test_admin.py` — `test_start_remote_daemon_stops_created_browser_when_daemon_start_fails` (:421-444), `..._when_daemon_start_is_interrupted` (:447-471, KeyboardInterrupt/SystemExit parametrized), `test_stop_cloud_browser_swallows_baseexception_from_stop_request` (:474-478), `test_start_remote_daemon_does_not_stop_created_browser_on_success` (:480-499), `test_strict_remote_stop_propagates_daemon_error` (:70-79), `test_remote_start_retries_cleanup_and_preserves_both_failures` (:82-110: exactly 3 stop attempts, exception strings `[start, cleanup]` preserved). Live-view suppression has NO direct unit test — deterministic env-matrix probe against pinned source substitutes (lane precedent).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "start_remote_daemon cloud browser stop", limit: 10, fields: ["signature", "file"] });
```
Resolves the trio at post-drift positions (verified live this pass).

## Verdict
Adopt create-before-attach + BaseException compensation, bounded cleanup retries, twin-failure exception groups, and pre-provisioning evaluation of display flags for any metered remote resource. Adapt API/env plumbing and flag vocabulary. Omit the profile-sync shell-out unless porting cookie migration too.
