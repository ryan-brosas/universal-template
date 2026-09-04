<!-- capsule-v2 -->
# Idle-handoff poll loop — when may a background poller close a browser another task might be using?

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb`; Codebase Memory `linkedin-mcp-server`. **Question:** How does an idle owner release a shared browser promptly without killing an in-flight call?

## Poll + counter + min-hold window
**Path/Symbol:** `linkedin_mcp_server/drivers/browser.py:watch_for_handoff_requests` (:960), `release_profile_if_idle_or_requested` (:982), `_close_unless_a_call_arrived` (:1050), `_close_browser_if_still_idle` (:1072); counters `note_call_started` (:942)/`note_activity` (:948).
**Signature:** `async def watch_for_handoff_requests() -> None` (1.0s cadence, `_HANDOFF_POLL_INTERVAL_SECONDS`); `async def release_profile_if_idle_or_requested() -> bool`.
**Data Shape:** `_calls_in_flight: int` incremented at call start, decremented in `note_activity()` which also stamps `_last_activity = time.monotonic()`; `idle_for=None` means no call has EVER run (idle in the strongest sense).

### Decisive source (the scheduling-point trap)
```text
Why polling at all: checking only between calls misses the owner that
finished its last call and went idle — a waiter announcing one second later
would wait out its whole budget against a browser nobody is using.

The guard must sit INSIDE the teardown coroutine:
    async def _close_unless_a_call_arrived() -> bool:
        async with _browser_lifecycle_lock:
            return await _run_deferring_cancels(_close_browser_if_still_idle())
    async def _close_browser_if_still_idle() -> bool:
        if _calls_in_flight > 0:
            return False                      # call claimed it during our wait
        if _browser is None:
            return False                      # another close already ran
        await _close_browser_locked()
        return True

Measured failure it prevents: checking the counter in the CALLER and then
starting the teardown as a task leaves a gap — asyncio.create_task does not
begin the coroutine, the loop runs other ready work first, a tool call took
the live browser through the fast path, and the teardown closed THAT browser
with one call in flight.

Min-hold window (handoff branch only):
    held = lease.held_seconds                # from ACQUISITION, not idleness
    never_worked = idle_for is None
    if never_worked or held >= config.browser_min_hold_seconds:
        return await _close_unless_a_call_arrived()
Idle-based test would always pass post-call, so the window would never apply;
it bounds reopen storms (every handoff costs a /feed/ revalidation).
```

**Flow:** background task sleeps 1s → `release_profile_if_idle_or_requested` → bail if no browser/lease or calls in flight → handoff requested? honor min-hold measured from acquisition → else idle timeout (`timeout > 0 and idle_for >= timeout`) → conditional close under lifecycle lock with in-coroutine re-check. Poll failures are logged debug and swallowed — next tool call checks again anyway.
**Invariant:** A conditional close NEVER runs with a stale in-flight count: the decision is re-made inside the same critical section as the teardown, after acquiring the lock a concurrent call could have been waiting behind. Deliberate closes (`close_session`, shutdown, login, import) bypass the counter — the guard lives in the conditional caller, not in `close_browser`.
**Probe:** `grep -c 'held >= config.browser_min_hold_seconds' linkedin_mcp_server/drivers/browser.py` → 1; `grep -c 'def test_an_idle_owner_exits' tests/test_daemon_liveness.py` → 1; integration coverage: `tests/test_profile_lease_integration.py`, watcher wired in `tests/test_server.py:399`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "release_profile_if_idle_or_requested handoff idle close", limit: 5 });
```

## Verdict
Adopt poll-based handoff with an in-coroutine recheck for any shared singleton serving bursty callers. Adapt intervals/min-hold to workload. Omit the LinkedIn feed-revalidation cost model (your reopen cost differs).
