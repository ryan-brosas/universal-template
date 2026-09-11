<!-- capsule-v2 -->

# Critical service heartbeat backoff — How does a periodic background loop distinguish an outage from death, and when does it give up?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect`. **Question:** What error taxonomy and interval arithmetic let a heartbeat loop survive flaky networks but exit on prolonged failure?

## Seeded success-window over transport/5xx-only errors; exponential interval doubling with reset-on-success; exit after N consecutive failure groups

**Path/Symbol:** `src/prefect/utilities/services.py:critical_service_loop (21-156)` (snippet-resolved; 23 inbound callers in graph). Retrieve anchor: `critical_service_loop Function 21-156`.

**Signature:** `async critical_service_loop(workload, interval: float, memory: int = 10, consecutive: int = 3, backoff: int = 1, printer=print, run_once=False, jitter_range: Optional[float] = None) -> None`.

**Data Shape:** `track_record: deque[bool]` seeded `[True] * consecutive`, `maxlen=consecutive`; `failures: deque[(Exception, tb)]` maxlen=memory; `backoff_count: int`.

### Decisive source
```python
track_record = deque([True] * consecutive, maxlen=consecutive)
while True:
    try:
        await workload()
        if backoff_count > 0:
            printer("Resetting backoff due to successful run.")
            backoff_count = 0
        track_record.append(True)
    except httpx.TransportError as exc:            # comms errors only — NOT
        track_record.append(False)                 # routine HTTP status codes
        failures.append((exc, exc.__traceback__))
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code >= 500:        # 5xx == probable outage
            track_record.append(False); failures.append(...)
        else:
            raise                                  # 4xx is a bug: die now
    if not any(track_record):                      # N truly-consecutive failures
        printer(f"Failed the last {consecutive} attempts. ...")
        for exception, traceback in distinct(reversed(failures),
                                             key=lambda p: type(p[0])):
            printer("".join(format_exception(None, exception, traceback)))
        backoff_count += 1
        if backoff_count >= backoff:
            raise RuntimeError("Service exceeded error threshold.")
        track_record.extend([True] * consecutive)  # restart the window
        failures.clear()
    ...
    sleep = (clamped_poisson_interval(interval, clamping_factor=jitter_range)
             if jitter_range is not None else interval * 2**backoff_count)
    await anyio.sleep(sleep)
```

**Flow:** the loop classifies ONLY transient-failure shapes (transport errors, HTTP ≥500); anything else propagates immediately, and BaseException (KeyboardInterrupt) is never captured. The seeded-all-success deque means a verdict requires genuinely `consecutive` failures with zero successes interleaved — background noise at a few percent error never trips it. When it trips, the loop prints a type-deduplicated digest of recent failures, doubles its sleeping interval (`interval * 2**backoff_count`) or draws clamped-Poisson jitter within `interval*(1±range)` to avoid thundering-herd alignment, resets the window, and keeps going; one success anywhere resets `backoff_count`. After `backoff` consecutive failure GROUPS it exits with RuntimeError. Callers here are observer `_start_polling_task`s (FlowRunCancellingObserver / FlowRunSuspendingObserver) — this loop IS the poll-plane fallback when the event stream is unavailable.

**Invariant:** (1) Error classification precedes counting: only plausible-outage exceptions feed the window. (2) The window is seeded successful so partial failure rates can't trigger backoff. (3) Backoff is group-based with reset-on-success — a single good call restores full cadence. (4) Exit is loud and typed (RuntimeError), after printing actionable diagnostics, never silent.

**Probe:** direct tests `tests/utilities/test_services.py`: `:24-39 operates_normally`, `:42-48 does_not_capture_keyboard_interrupt`, `:51-102 tolerates {single, two-consecutive, majority} intermittent errors`, `:105-125 quits_after_3_consecutive_errors` (await_count == 4 + digest in stdout), `:184-209 captures_all_http_500_errors` vs `:212-227 does_not_capture_other_http_status_errors` (403 re-raised, count == 2), `:230-254 backoff_quits_after_6_consecutive_errors_twice`, `:284-314 backoff_reset_on_success`, `:317-354 backoff_increases_interval_on_each_consecutive_group` (sleeps 1·2+2·3+4·3+8·3+16·3+32 asserted), `:158-181 jittered_sleeps_within_clamp_bounds`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "^critical_service_loop$", "limit": 3}'
```
(observed rank-1 line-exact: `critical_service_loop Function src/prefect/utilities/services.py 21-156`)

## Verdict
Adopt the classify→window→digest→double→reset ladder for every must-keep-running periodic job; adapt the exception set to your transport and the consecutive/backoff constants to your SLO; omit Prefect's printer/capsys-friendly diagnostics shape if unneeded.
