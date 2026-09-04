<!-- capsule-v2 -->
# Daemon shutdown/recovery barrier — how do you stop a daemon that owns a billable cloud browser without orphaning it, and what stays retryable when cleanup fails?

**Source:** browser-harness MIT `main@6bb1c847fd62638554618e8d1e03247b935ff9cf`; Codebase Memory `browser-harness`. **Question:** When an orchestrator asks the daemon to shut down, which state flips first, which concurrent recoveries must be cancelled+drained before any owned target is touched, and why must the daemon survive its own failed cleanup?

## Shutdown barrier + bounded recovery drain
**Path/Symbol:** `src/browser_harness/daemon.py`: module latch `_REMOTE_STOPPED` (:90) + `RECOVERY_CANCEL_DRAIN_TIMEOUT = 2` (:97-99); `stop_remote(strict=False)` (:309-336); `Daemon._begin_recovery` (:542-552) / `_finish_recovery` (:554-558) / `_cancel_and_drain_recoveries` (:560-575); `Daemon.handle` shutdown meta (:696-717); stale-session branch registration window (:726-763); `serve()` finalization (:767-819).

**Signature:** `def stop_remote(strict=False) -> bool`; `async def _cancel_and_drain_recoveries() -> bool`; `async def handle(self, req) -> dict`.

**Data Shape:** `_REMOTE_STOPPED` is a module-global idempotence latch; recovery handlers register their own `asyncio.current_task()` in `self._recovery_tasks` (a set) with `self._active_recoveries` counter and a `_recoveries_idle` Event. `handle({"meta": "shutdown"})` returns either `{"ok": True}` or `{"error": <str>}` — never raises to the client.

### Decisive source
```python
if meta == "shutdown":
    # Flip the barrier synchronously with recovery registration, then
    # cancel/drain existing handlers. In particular, a CDP replay that
    # never answers must not prevent Cloud cleanup from being attempted.
    if self._shutting_down:
        return {"error": "shutdown already in progress"}
    self._shutting_down = True
    if not await self._cancel_and_drain_recoveries():
        # Preserve the daemon as a retryable cleanup authority. The
        # strict caller will leave its endpoint and PID file intact.
        self._shutting_down = False
        return {"error": "stale-session recovery did not stop"}
    try:
        stop_remote(strict=True)
    except Exception as e:
        # A failed Cloud stop must leave the daemon usable so a later
        # shutdown request can retry the billable-browser cleanup.
        async with self._session_state_lock:
            self._shutting_down = False
        return {"error": str(e)}
    self.stop.set()
    return {"ok": True}
```

**Flow:** shutdown request → duplicate-shutdown rejected → `_shutting_down = True` (synchronous with the registration gate, so no *new* recovery can register) → active recovery tasks cancelled and awaited under a bounded 2s drain (`asyncio.wait(..., timeout=RECOVERY_CANCEL_DRAIN_TIMEOUT)`; returns False if any task is still pending or the idle Event is clear) → drain failure **rolls the barrier back** so the daemon remains a retryable cleanup authority → `stop_remote(strict=True)` PATCHes `{action: "stop"}` to Browser Use with 3 attempts, `0.5*(attempt+1)` backoff, latch set only on success → Cloud-stop failure also rolls back (under `_session_state_lock`) and returns the error string → success sets `self.stop`, and `serve()`'s finalization then closes the dedicated tab under `_session_state_lock` → `_dedicated_target_lock` taken in the same order recovery takes them, skipping cleanup entirely when recoveries did not stop. The crash path is covered too: a server crash/cancellation never passes through `meta=shutdown`, so `serve()`'s `finally` establishes the same barrier itself (`d._shutting_down = True` → drain → conditional close). Stale-session handlers wrap their whole recovery window in `try/ finally: self._finish_recovery(recovery_task)` with an in-lock `_shutting_down` re-check that answers `{"error": "daemon is shutting down"}` instead of recovering into a dying process.

**Invariant:** A failed cleanup must never be silently swallowed AND must never leave the daemon unusable — every failure path (drain timeout, cloud-stop error) rolls the barrier back so a later `shutdown` can retry; `_REMOTE_STOPPED` makes repeated `stop_remote` calls idempotent; the dedicated tab close happens only after the barrier + successful drain, so tab cleanup can never race a recovery re-attach. Upstream inverted its own old invariant: `test_shutdown_closes_only_the_daemon_owned_tab` now asserts `closed == ["daemon-tab"]` (the pre-drift test asserted `closed == []`).

**Probe:** `tests/unit/test_daemon.py` — `test_remote_stop_retries_and_succeeds` (:24-41: three urlopen attempts all timeout=15, then `_REMOTE_STOPPED is True`); `test_shutdown_keeps_daemon_alive_when_cloud_stop_fails` (:44-56: response == `{"error": "billing stop failed"}` and `d.stop.is_set() is False`); `test_shutdown_closes_only_the_daemon_owned_tab` (:588-613: `closed == ["daemon-tab"]`, `dedicated_target_id is None`, user tab untouched); `test_delayed_stale_request_follows_recovery_during_domain_enable` (:616-678) and `test_tab_switch_waits_for_recovery_and_keeps_old_action_on_old_tab` (:681-753: recovered action lands on the OLD tab, `redirected == []`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "stop_remote recovery drain shutdown barrier", limit: 10, fields: ["signature", "lines"] });
```
Resolves `daemon.stop_remote` :309-336, `Daemon._begin_recovery`/:542-552, `_finish_recovery`/:554-558, `_cancel_and_drain_recoveries`/:560-575, plus all four direct tests (verified live this pass).

## Verdict
Adopt the barrier-then-drain-then-cleanup ordering, the rollback-on-failed-cleanup posture (daemon as retryable cleanup authority), the module-level stop latch, and the crash-path finalization that re-establishes the barrier; adapt the 2s drain bound, 3-attempt/0.5·(n+1) backoff, and lock order to your host's session model; omit the Browser Use PATCH specifics. Coverage caveat: none — this seam gained direct upstream unit tests at this pin (previously absent); `test_daemon.py`/`test_macos.py` remain ambient-collection-blocked (`cdp_use` missing) but were read and anchor-verified, and the four barrier tests above execute GREEN under the lane's ambient suite selection.
