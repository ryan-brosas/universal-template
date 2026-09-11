<!-- capsule-v2 -->
# Modification wait, fail-open — How do you pause execution for pending planner edits without ever deadlocking?

**Source:** ufo (MIT) `main@96983c73ed09`; Codebase Memory `ufo`. **Question:** When the orchestrator must not read the DAG while an agent is editing it, how do you wait for those edits yet guarantee forward progress if they never land?

## Snapshot-recheck wait loop with one time budget
**Path/Symbol:** `galaxy/session/observers/constellation_sync_observer.py:ConstellationModificationSynchronizer.wait_for_pending_modifications` (:247-311).
**Signature:** `async def wait_for_pending_modifications(self, timeout: Optional[float] = None) -> bool` (True = all completed; False = timed out and proceeded anyway).
**Data Shape:** `_pending_modifications: Dict[name, Future]`; default timeout `self._modification_timeout`.

### Decisive source
```python
while self._pending_modifications:
    # Get current pending tasks (snapshot)
    pending_futures = list(self._pending_modifications.values())
    elapsed = asyncio.get_event_loop().time() - start_time
    remaining_timeout = timeout - elapsed
    if remaining_timeout <= 0:
        raise asyncio.TimeoutError()
    await asyncio.wait_for(
        asyncio.gather(*pending_futures, return_exceptions=True),
        timeout=remaining_timeout,
    )
    # If new modifications were added during the wait, loop again
    if not self._pending_modifications:
        break
    await asyncio.sleep(0.01)
...
except asyncio.TimeoutError:
    self.logger.warning(
        f"⚠️ Timeout waiting for modifications after {timeout}s. "
        f"Proceeding anyway. Pending: {pending}")
    # Clear all pending modifications to prevent permanent deadlock
    self._pending_modifications.clear()
    return False
```

**Flow:** no-op return True when nothing is pending → loop: snapshot current futures, compute one shared remaining-time budget, gather them under `wait_for` → re-check for newly registered edits added during the wait (loop again) → on total timeout, log, CLEAR all pending entries, and return False so the caller proceeds rather than blocking forever.
**Invariant:** the timeout budget spans the whole wait, not per-snapshot; a timeout must both release the caller AND drain `_pending_modifications`, otherwise stale futures would trip every future wait.
**Probe:** `tests/test_constellation_sync_observer.py:280-294+` (`TestTimeoutHandling.test_modification_timeout`) pins that a short timeout (`set_modification_timeout(0.5)`) returns False while a modification is still pending.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ufo", query: "wait for pending modifications timeout", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt fail-open semantics for any liveness-critical gate over external input: timeouts must clear the gate state, not just give up this round. Adopt the snapshot-recheck pattern to handle registrations arriving mid-wait. Adapt the 0.01 s settle delay and logging verbosity. Omit UFO's event-bus coupling (`on_event` registers/clears pendings) unless porting that observer too.
