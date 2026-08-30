<!-- capsule-v2 -->
# Event-driven CDP session pool — targets and sessions are separate entities with refcounted removal

**Source:** browser-use MIT `main@3c989dc0`; Codebase Memory `browser-use`. **Question:** How do you keep a CDP session pool exactly equal to browser reality without polling, when multiple sessions can attach to one target?

## SessionManager: two dicts + two mappings under ONE lock
**Path/Symbol:** `browser_use/browser/session_manager.py:SessionManager` (19-60): `_targets`, `_sessions`, `_target_sessions: dict[TargetID, set[SessionID]]`, `_session_to_target`; handlers `_handle_target_attached` (402-508), `_handle_target_detached` (530-634), `_initialize_existing_targets` (784-878).
**Signature:** `async def _handle_target_attached(self, event: AttachedToTargetEvent) -> None` / `... _handle_target_detached(self, event)`
**Data Shape:** Target = entity (page/iframe/worker); CDPSession = communication channel. A target is removed ONLY when its session set hits empty; TabClosedEvent fires only for fully-removed page/tab types.

### Decisive source
```python
# attach handler:
# Enable auto-attach for this session's children (do this FIRST, outside lock)
await ...send.Target.setAutoAttach(params={'autoAttach': True, 'waitForDebuggerOnStart': False, 'flatten': True}, session_id=session_id)
except Exception as e:
    # Expected for short-lived targets (workers, temp iframes) that detach before this executes
    if '-32001' not in error_str and 'Session with given id not found' not in error_str: ...
# detach handler:
self._target_sessions[target_id].discard(session_id)
remaining_sessions = len(self._target_sessions[target_id])
if remaining_sessions == 0:
    ...
    if agent_focus_lost: self.browser_session.agent_focus_target_id = None   # clear INSIDE lock
    self._targets.pop(target_id); del self._target_sessions[target_id]
    self._lifecycle_events.pop(target_id, None)
```

**Flow:** `start_monitoring` → `Target.setDiscoverTargets(filter=[page,iframe])` → register 4 handlers → `_initialize_existing_targets` attaches to every pre-existing target (attach-handler is idempotent, so Chrome's own attachedToTarget echoes are safe) → attach: setAutoAttach FIRST outside lock, then inside lock add session to target's set + create/update Target in the SAME critical section → page-type targets get `_enable_page_monitoring` → detach: discard session; target removed at zero sessions; stale focus cleared immediately.
**Invariant:** "Create or update Target inside the same lock so that get_target() is never called in the window between _target_sessions being set and _targets being set" (source comment :447). CDP error `-32001`/'Session with given id not found' is EXPECTED for short-lived workers/iframes and must not warn or fail. Detach events may omit targetId — resolve via `_session_to_target` first. Recovery runs OUTSIDE the lock so waiting operations aren't blocked.
**Probe:** no upstream unit file (tests/ci/browser/test_cdp_headers.py mocks SessionManager wholesale); deterministic pin: `grep -n "same lock so that get_target" browser_use/browser/session_manager.py` (:447-448). Coverage caveat: pool behavior verified by reading + graph line-exact anchors (`_handle_target_attached` resolves session_manager.py).
**Pattern family:** single-slot event registry — see session-manager-single-slot-handlers.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_handle_target_attached _handle_target_detached SessionManager", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the target/session entity split + refcounted removal + same-lock create-and-register for any CDP/WebSocket multiplexer; adapt the auto-attach filter types to your domain; omit proxy Fetch.enable hooking unless you authenticate proxies the same way.
