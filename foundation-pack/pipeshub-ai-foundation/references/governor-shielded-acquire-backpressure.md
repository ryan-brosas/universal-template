<!-- capsule-v2 -->
# Shielded acquire + cancel-race permit release — how do you queue a request on an admission gate for minutes without leaking a permit when the client disconnects?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** What is the exact asyncio choreography that lets warn-then-wait-then-429 backpressure coexist with external cancellation, so the gate's `in_use` never overcounts?

## Warn timeout shields; cancellation path cancels AND releases-if-granted
**Path/Symbol:** `backend/python/app/services/resource_governor/admission.py:acquire_gate_with_backpressure/_cancel_and_release_if_granted` (L33–136); HTTP consumer `api/routes/parsing.py` :147–219 (`classify → parse_cost → governor.gate(gate_pool(tier)) → acquire → 429 Retry-After → finally gate.release(cost)`).
**Signature:** `acquire_gate_with_backpressure(gate, cost, tier, message_id, *, logger, log_prefix, queue_wait_warn_seconds=10.0, gate_timeout_seconds=120.0) -> bool` — True admitted, False ⇒ caller answers 429.
**Data Shape:** two nested timeouts: WARN (log saturation, keep waiting) inside GATE-TIMEOUT (give up ⇒ 429 + `Retry-After: 5`); `SemaphoreLogger` acquire-attempt/acquired/error breadcrumbs keyed by message_id.

### Decisive source
```python
acquire_task = asyncio.ensure_future(gate.acquire(cost=cost,
                          timeout=gate_timeout_seconds))
try:
    admitted = await asyncio.wait_for(asyncio.shield(acquire_task),
                                      timeout=queue_wait_warn_seconds)
except asyncio.CancelledError:
    # shield() only protects acquire_task from wait_for's OWN timeout;
    # it does NOTHING about THIS coroutine being cancelled externally
    # (FastAPI request task cancelled on client disconnect). The detached
    # acquire keeps running and may WIN a permit in that race:
    await _cancel_and_release_if_granted(acquire_task, gate, cost)
    raise
except asyncio.TimeoutError:
    likely_rate_limited = gate.in_use < max_slots   # capacity free while
    # waiting ⇒ StartRateLimiter is the bottleneck, not the limit — named
    # in the log so this is diagnosable from logs alone
    ...  # log, then shield again and keep waiting to the gate deadline
    if not admitted: return False        # 429 backpressure path

async def _cancel_and_release_if_granted(acquire_task, gate, cost):
    acquire_task.cancel()
    with contextlib.suppress(asyncio.CancelledError, Exception):
        if await acquire_task:           # had it already been granted?
            gate.release(cost)           # else in_use overcounts forever
```

**Flow:** route classifies format/size into tier+cost → acquires the memoised per-pool gate through the backpressure helper → helper's warn branch logs "saturated" at 10s and continues to 120s → give-up returns False → route emits 429 with `Retry-After` and a details body carrying `{tier, limit}` (client's own longer-horizon retry takes over — a queue timeout must NEVER be treated as a service failure) → on success the ROUTE owns release in its `finally`, including for handler exceptions.
**Invariant:** (1) Every early-exit from the wait MUST pass through `_cancel_and_release_if_granted` — shield protects only against one specific canceller; the dedicated test drives the race tick-by-tick until `in_use==1`, cancels, and asserts `in_use==0`. (2) The second `await asyncio.shield(acquire_task)` after the warn timeout is equally mandatory: cancelling directly would discard a permit already won. (3) False-from-helper is a CONTRACT: callers respond with backpressure, not error semantics. (4) Release ownership stays at the route layer (`finally`) because the helper returns instead of raising — pairing them wrongly double-releases or leaks. (5) `gate.limit − in_use` is safe as a "free slots" log gauge only AFTER admission settles (in_use changes concurrently).
**Probe:** `tests/unit/services/resource_governor/test_admission.py` :25–125 (immediate admit :26, warn-past-threshold-then-admit :36, gate-timeout-no-permit-leak :56, within-warn-skips-branch :70, **caller-cancelled-mid-wait-does-not-leak-a-permit :89–124** — the race regression test); route-level `tests/unit/api/routes/test_parsing_routes.py`.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project mnt-hdd-utopia-inspo-platforms-pipeshub-ai --query "acquire_gate_with_backpressure" --detail ids
```

## Verdict
Adopt the shield+cancel-release choreography verbatim wherever long queue waits meet cancellable requests; adopt the two-timeout warn/wait/429 shape for any human-facing admission front-end. Adapt timeouts and log vocabulary. Omit nothing — every branch is test-pinned upstream. Coverage: dedicated suite incl. the exact leak race; runner-block caveat in work record [DONE:188].
