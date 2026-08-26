<!-- capsule-v2 -->
# Storage-state watchdog — cookie/localStorage persistence with atomic save ladder

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does a browser agent persist and restore cookies + localStorage to a Playwright-style storage_state file, safely across crashes?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/watchdogs/storage_state_watchdog.py` (373 lines): `StorageStateWatchdog` (:25) — `on_BrowserConnectedEvent` (:49-57, start monitoring + auto-load), `on_SaveStorageStateEvent` (:64-66), `on_LoadStorageStateEvent` (:68-70), `_save_storage_state` (:158-222), `_load_storage_state` (:224-321), `_merge_storage_states` (:323-345), `_have_cookies_changed` (:135-156), `_monitor_storage_changes` (:119-133).
**Signature:** `_save_storage_state(path=None)`; `_load_storage_state(path=None)`; auto-save every `auto_save_interval=30.0`s when cookies change.

### Decisive source
```python
# Save (atomic ladder, guarded by _save_lock):
#   - skip if storage_state is already a dict (in-memory, never stringify)
#   - _cdp_get_storage_state() -> {cookies, origins}; update _last_cookie_state
#   - merge with existing file (cookie key = (name,domain,path); origin key = origin)
#   - write temp .json.tmp -> backup existing to .json.bak -> replace temp->final
# Load:
#   - expires in (0,0.0,-1,-1.0) are session cookies: OMIT expires (CDP treats expires=0 as expired)
#   - cookies via _cdp_set_cookies; origins via _cdp_add_init_script scoped to window.location.origin
#     (origin-scope guard prevents cross-site pollution)
# Change detection: compare {(name,domain,path): value} sets between current and last
```

**Flow:** on connect → start monitor task + auto-load; monitor loop polls every 30s, saves on cookie-set change; save is a merge-then-atomic-replace under a lock; load normalizes session cookies (drops expires 0/-1) and injects localStorage/sessionStorage via origin-scoped init scripts.
**Invariant:** the save is crash-safe (temp→bak→final); in-memory dict storage states are never stringified (would leak cookie values into logs/events); session cookies must drop `expires` else CDP treats them as expired; localStorage restoration is origin-scoped to avoid cross-site pollution.
**Probe:** `tests/ci/test_action_LoadStorageStateEvent.py`, `tests/ci/browser/test_session_start.py`, `tests/ci/test_profile_copy.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "StorageStateWatchdog _save_storage_state _load_storage_state _merge_storage_states expires session cookie", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the atomic save ladder, the session-cookie expires-normalization, the origin-scoped localStorage restore, and the (name,domain,path) cookie merge key. Adapt the CDP cookie API to host.
