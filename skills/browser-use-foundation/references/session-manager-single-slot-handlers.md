<!-- capsule-v2 -->
# Single-slot CDP event registry — why per-tab lifecycle handlers silently freeze all but one tab

**Source:** browser-use MIT `main@3c989dc0`; Codebase Memory `browser-use`. **Question:** When an event bus allows only ONE handler per CDP method, how do you fan lifecycle events out to N tabs?

## ONE global Page.lifecycleEvent handler routed by session_id
**Path/Symbol:** `browser_use/browser/session_manager.py:start_monitoring.on_lifecycle_event` (112-132) + `_lifecycle_events: dict[TargetID, deque]` (53) + `get_lifecycle_events` (139-145) + `_enable_page_monitoring` (880-918).
**Signature:** `def on_lifecycle_event(event, session_id: SessionID | None = None)` (sync — "Register synchronous event handlers (CDP requirement)")
**Data Shape:** per-target ring buffer `deque(maxlen=50)` of `{name, loaderId, timestamp(loop-time)}`; the SAME deque object is exposed on each CDPSession as `session._lifecycle_events` for readiness checks.

### Decisive source
```python
# Page lifecycle events per target, fed by ONE global Page.lifecycleEvent handler
# registered in start_monitoring(). cdp-use's event registry is single-slot per
# CDP method, so per-session handler registrations would replace each other and
# leave every tab but the most recently attached one without lifecycle events.
self._lifecycle_events: dict[TargetID, deque[dict[str, Any]]] = {}
...
def on_lifecycle_event(event, session_id=None):
    # Registering per-session closures instead would clobber each other in
    # cdp-use's single-slot registry (one handler per CDP method).
    if not session_id: return
    target_id = self.get_target_id_from_session_id(session_id)
    if not target_id: return
    self.get_lifecycle_events(target_id).append({...})
```

**Flow:** start_monitoring registers exactly four global handlers (attached/detached/targetInfoChanged/lifecycle) → each lifecycle event arrives with its session_id → reverse-map to target_id → append into that target's bounded deque → navigation code consumes the deque; `_enable_page_monitoring` only enables Page/Network domains and shares the buffer reference.
**Invariant:** NEVER register a second Page.lifecycleEvent closure anywhere else — it replaces the global one and every earlier tab freezes. Handlers are sync functions that spawn tasks via `create_task_with_error_handling(..., suppress_exceptions=True)`; heavy work must not run inline in the callback. Ring buffer (maxlen=50) bounds memory across long sessions.
**Probe:** deterministic source pin: `grep -n "single-slot" browser_use/browser/session_manager.py` (:50-52 and :903-904 — documented at BOTH registration and enable sites). Coverage caveat: no upstream test pins the clobber behavior; it is stated in-source twice.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "on_lifecycle_event get_lifecycle_events _enable_page_monitoring", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt global-handler + session→target routing + per-target ring buffers whenever your client library has single-slot registries (cdp-use today; several WS libs historically); adapt buffer size; omit timestamp loop-clock choice if you need wall time.
