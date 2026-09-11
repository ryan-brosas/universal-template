<!-- capsule-v2 -->
# Agent-focus recovery ladder — event-driven stale-focus repair with emergency fallback tab

**Source:** browser-use MIT `main@3c989dc0`; Codebase Memory `browser-use`. **Question:** When the tab the agent is focused on crashes or detaches, how do you restore focus without polling and without two recoveries racing?

## _recover_agent_focus + ensure_valid_focus: lock-guarded, event-coordinated
**Path/Symbol:** `browser_use/browser/session_manager.py:_recover_agent_focus` (636-782), `ensure_valid_focus` (321-400), `_get_session_for_target` stale-focus branch (159-181); state `_recovery_in_progress`, `_recovery_complete_event`, `_recovery_task` (59-61).
**Signature:** `async def _recover_agent_focus(self, crashed_target_id: TargetID) -> None`; `async def ensure_valid_focus(self, timeout: float = 3.0) -> bool`
**Data Shape:** recovery lock serializes attempts; a completion asyncio.Event lets N waiters observe one recovery; final reset happens in `finally`.

### Decisive source
```python
async with self._recovery_lock:
    if self._recovery_in_progress:      # join ongoing recovery instead of duplicating
        ... await asyncio.wait_for(self._recovery_complete_event.wait(), timeout=5.0)
        return
    self._recovery_in_progress = True
    self._recovery_complete_event = asyncio.Event()
    # Check if another recovery already fixed agent_focus
    if self.browser_session.agent_focus_target_id and ... != crashed_target_id:
        return
# Perform recovery (outside lock to allow concurrent operations)
page_targets = self.get_all_page_targets()
if page_targets:
    new_target_id = page_targets[-1].target_id; is_existing_tab = True   # most recent page
else:
    new_target_id = await self.browser_session._cdp_create_new_page('about:blank')
    ... dispatch TabCreatedEvent ...
for attempt in range(20):               # wait up to 2s for Chrome's attach EVENT
    await asyncio.sleep(0.1); new_session = self._get_session_for_target(new_target_id)
    if new_session: break
...
finally:
    if self._recovery_complete_event: self._recovery_complete_event.set()
    self._recovery_in_progress = False; self._recovery_task = None
```

**Flow:** detach handler clears focus + spawns recovery task (only if none in progress) → under recovery lock: dedupe/join → re-check whether focus was already fixed post-await → pick most recent surviving page OR create about:blank tab (+ TabCreatedEvent so watchdogs initialize) → bounded 2s wait for the CDP attachedToTarget event to materialize a session ("This polling is necessary - waiting for external Chrome CDP event") → set focus, activate tab visually, dispatch AgentFocusChangedEvent → on failure: create EMERGENCY fallback tab and retry once → critical log if even that fails → finally: set event, clear flags.
**Invariant:** waiters never poll browser state — `ensure_valid_focus` awaits `_recovery_complete_event` with timeout and re-checks ONCE after wake. Post-await re-checks (`agent_focus != crashed_target_id`) defer to concurrent fixes. The `finally` must ALWAYS signal completion or every future waiter times out. Recovery work runs outside the lock; only claim/release is inside.
**Probe:** deterministic source pins: `grep -n "emergency fallback tab" browser_use/browser/session_manager.py` (:745/:749); `"Recovery state reset"` (:782). Coverage caveat: no upstream unit file (needs live CDP).
**Retrieve note:** graph anchor `_recover_agent_focus` resolves at session_manager.py.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_recover_agent_focus ensure_valid_focus", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the claim-inside-lock/work-outside-lock + completion-event broadcast ladder for any "repair shared pointer after crash" flow; adapt the fallback-tab policy to your app's notion of a safe blank state; omit the visual Target.activateTarget call if headless-only.
