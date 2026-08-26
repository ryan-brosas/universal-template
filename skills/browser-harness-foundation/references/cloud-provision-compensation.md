<!-- capsule-v2 -->
# Cloud-browser provisioning compensation — how do you provision a billed resource without leaking it when startup fails?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** What is the create→attach→compensate contract for remote browser sessions (and their profile-name resolution)?

## Create-BEFORE-attach with BaseException-wide undo
**Path/Symbol:** `src/browser_harness/admin.py:start_remote_daemon/_stop_cloud_browser/_resolve_profile_name` (:547-655, :616-623).
**Signature:** `start_remote_daemon(name="remote", profileName=None, **create_kwargs) -> dict`; `_stop_cloud_browser(browser_id)` swallows BaseException; `_resolve_profile_name(name) -> uuid`.
**Data Shape:** `POST /browsers` returns `{id, cdpUrl, liveUrl, ...}`; daemon env gets `BU_CDP_WS` (resolved from cdpUrl via `/json/version`) + `BU_BROWSER_ID`.

### Decisive source
```python
browser = _browser_use("/browsers", "POST", create_kwargs)
try:
    ensure_daemon(
        name=name,
        env={"BU_CDP_WS": _cdp_ws_from_url(browser["cdpUrl"]), "BU_BROWSER_ID": browser["id"]},
    )
except BaseException:
    _stop_cloud_browser(browser.get("id"))
    raise
_show_live_url(browser.get("liveUrl"))
```

**Flow:** refuse if daemon already alive → profileName resolved client-side via paginated listing (0 or >1 exact-name matches ⇒ loud RuntimeError suggesting profileId) → POST create → ensure_daemon(env) → ANY failure incl. KeyboardInterrupt/SystemExit PATCHes `/browsers/{id} {action:"stop"}` (billing ends, profile persists) → re-raise.
**Invariant:** The compensation catch must be `BaseException` — Ctrl-C between create and attach would otherwise orphan a BILLED cloud browser; cleanup itself swallows BaseException so it can never mask the original error; success never stops the browser; ambiguous profile names refuse to guess.
**Probe:** `tests/unit/test_admin.py:335-413` — POST then PATCH-stop on RuntimeError AND on KeyboardInterrupt/SystemExit; stop swallows provider-raised BaseException; success path issues exactly one POST.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "start_remote_daemon cloud browser stop", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt create-before-attach + BaseException compensation for any metered remote resource. Adapt API/env plumbing. Omit the profile-sync shell-out unless porting cookie migration too.
