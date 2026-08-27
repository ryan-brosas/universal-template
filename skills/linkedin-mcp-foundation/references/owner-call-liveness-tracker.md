<!-- capsule-v2 -->
# Owner-side call-liveness tracker — stop work nobody wants, without killing work you cannot identify

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb2907`; Codebase Memory `linkedin-mcp-server`. **Question:** Given that cancellation does not cross a loopback hop, how does a long-lived owner decide which of its running calls to abandon — distinguishing "the client left" from "this process was not scheduled" from "we are shutting down" from "a client we cannot identify is still waiting"?

## CallLiveness + OwnerCallLivenessMiddleware in daemon_liveness.py
**Path/Symbol:** `linkedin_mcp_server/daemon_liveness.py` — `CallLiveness` (:128-265): `watch` (:154-160), `call_started`/`call_finished` (:163-172), `the_endpoint_is_live` (:174-183), `quiet_for` (:185-200), `heard` (:202-213), `release` (:215-217), `cancel_the_abandoned` (:219-265); `OwnerCallLivenessMiddleware.on_call_tool` (:281-347); constants `HEARTBEAT_SECONDS=2.0` (:68), `EXPIRY_SECONDS=10.0` (:79), `_STALL_SECONDS=1.0` (:88). Companion capsule `server-role-and-liveness.md` covers the protocol/compatibility half (no version bump, optional-in-both-directions markers); this one covers the tracker's timing semantics.
**Signature:** `watch(call_id, task) -> None`; `quiet_for() -> float | None`; `cancel_the_abandoned() -> list[str]`; middleware registered OUTSIDE the serializing middleware.
**Data Shape:** Two separate counters: `_waiting: dict[call_id, _Waiting(task, last_heard)]` (marked calls only — the cancellable set) and `_in_flight: int` (ALL calls, marked or not). Plus `_quiet_since: float | None` (idle clock) and `_last_scan: float | None` (stall detection). Times are monotonic.

### Decisive source
```python
# :219-265 — the scan runs from the owner's own poll loop; a stall in the OWNER
# resets everyone's clock instead of charging it to the frontends
now = time.monotonic()
since_last = now - self._last_scan if self._last_scan is not None else 0.0
self._last_scan = now
if since_last > _STALL_SECONDS:
    # A laptop that slept, a machine under heavy load, or a long synchronous
    # stretch... Expiring on the tick after one of those would cancel calls
    # whose frontends were beating the whole time and never got heard.
    for entry in self._waiting.values():
        entry.last_heard = now
    return []

deadline = now - EXPIRY_SECONDS
abandoned = [call_id for call_id, entry in self._waiting.items()
             if entry.last_heard < deadline]
for call_id in abandoned:
    entry = self._waiting.pop(call_id)
    entry.task.cancel()
return abandoned

# :326-345 — cancellation triage inside the middleware
except asyncio.CancelledError:
    outer = asyncio.current_task()
    if outer is not None and outer.cancelling():
        raise                                   # shutdown, not abandonment
    if running.cancelled() and call_id not in _liveness._waiting:
        raise ToolError(                        # ours: stops here as an error
            "Stopped because the client that asked for it stopped waiting") from None
    raise
finally:
    _liveness.release(call_id)
```
**Flow:** every arriving call → call_started() (counted even when unmarked) → unmarked ⇒ plain await, never watched; marked ⇒ ensure_future + watch(call_id, task) with last_heard=now (the first heartbeat precedes dispatch, so the call starts already heard) → owner poll loop calls cancel_the_abandoned() each tick: stall > 1.0s ⇒ reset all clocks, cancel nothing (a stall buys ONE cycle, not immunity); else expire entries older than 10s and task.cancel() them → cancelled call surfaces as ToolError, not CancelledError → release + call_finished in finally. Idle exit: quiet_for() is None while any call runs OR while the endpoint is unpublished — the idle clock starts at descriptor publication, not process start.
**Invariant:** The cancellable set and the idleness set are DIFFERENT: an unmarked call cannot be cancelled (old frontends send no marker; newer shapes this build cannot read must also run to completion), but calling it idleness would exit the owner mid-call, cutting off exactly the frontends the build promises to serve. A gap between the owner's own scans longer than the stall threshold means the owner was not running — nobody is written off for it, and clocks restart rather than shift by the stall length (which for a stall longer than the expiry would push deadlines into the future). The relationship pins, not the numbers: EXPIRY ≥ 3×HEARTBEAT (one late beat cannot expire a live call) and _STALL > 5× the stand-down poll interval (below the poll, expiry is switched off). Middleware placement outside the serializing layer is deliberate: a call queued behind another is the commonest abandonment case; inside, it becomes cancellable only after it has taken the browser. Shutdown and abandonment are told apart by the OUTER task's cancelling counter, because both can arrive at the same child in the same tick.
**Probe:** `tests/test_daemon_liveness.py` — `TestCountingWhoIsWaiting` (:72-140) pins cancel-on-silence, leave-alone-on-beat, unknown-beat-noop, release-stops-watching, and both relationship pins (`_STALL_SECONDS > _STAND_DOWN_POLL_SECONDS * 5`, `EXPIRY_SECONDS >= 3 * HEARTBEAT_SECONDS`); `TestTheOwnerSideMiddleware` (:141-267) pins unmarked-never-watched, marked-released-after-failure, abandoned-becomes-ToolError, shutdown-not-swallowed; `TestAnOwnerThatWasNotRunning` (:867-910) pins late-scan-expires-nothing and next-scan-judges-normally; `TestTellingShutdownFromAbandonment` (:910-953) pins the same-tick race; `TestGoingAwayWhenNobodyNeedsIt` (:632-740) pins endpoint-publication clock start, in-flight-holds-the-door (marked AND unmarked), and clock-restart-on-call-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "CallLiveness cancel_the_abandoned quiet_for OwnerCallLivenessMiddleware", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-counter split (cancellable vs merely-running) plus stall-aware expiry driven from an existing poll loop, for any long-lived server that proxies long calls behind a transport where cancellation does not propagate. Adopt the three-way cancellation triage (shutdown / ours / foreign) whenever your own expiry mechanism can race a process-wide cancel. Adapt cadence/expiry/stall constants to your measured round-trip and worst-case loop-blocking times — pin the RELATIONSHIPS in tests, not the numbers. Omit the MCP header specifics. Coverage caveat: none — daemon_liveness.py fully indexed at the pin (no_recorded_issue); graph unavailable this pass, citations verified by direct read.
