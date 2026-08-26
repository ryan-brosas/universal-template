<!-- capsule-v2 -->
# wait_for_all_checks quiescence protocol — how do tests and the UI know every watch is truly done?

**Source:** changedetection.io Apache-2.0 `master@fce24780`; Codebase Memory `ext-changedetection.io`. **Question:** What exact conditions define "all checks finished", and why is a stabilization window required?

## Connected graph-selected seam
**Path/Symbol:** `changedetectionio/worker_pool.py:wait_for_all_checks` (:519-565); test wrapper `tests/util.py:wait_for_all_checks` (:201-208); race-comment in `worker.py` :90-92.
**Signature:** `wait_for_all_checks(update_q, timeout=150) -> bool` (True = quiesced, False = timeout).
**Data Shape:** Polls two independent signals each iteration: `update_q.qsize() == 0` AND `len(get_running_uuids()) == 0`. Adaptive sleep ladder 0.2s (first 10) → 0.4s (to 30) → 0.8s.

### Decisive source
```python
if q_length == 0 and not any_workers_busy:
    if empty_since is None:
        empty_since = time.time()
    # Brief stabilization period for async workers
    elif time.time() - empty_since >= 0.3:
        # Add small buffer for filesystem operations to complete
        time.sleep(0.2)
        return True
else:
    empty_since = None
```

**Flow:** Quiescence = queue drained + zero claimed UUIDs, held stable for ≥0.3s, plus a final 0.2s filesystem buffer before returning. Any busy observation resets `empty_since`, so flapping (job re-queued by claim-defer, worker mid-write) cannot produce a false idle. The claim must happen immediately after dequeue precisely because this predicate reads qsize and running set as separate signals — late claiming would show an item "in neither" place and fake a pass.
**Invariant:** Two-signal AND with stability window is the contract; checking only qsize is WRONG (workers still processing), checking only running-set is WRONG (queue backlog). Timeout returns False, never raises — callers treat it as best-effort.
**Probe:** `grep -c 'empty_since' changedetectionio/worker_pool.py` → `5`; `grep -c 'def wait_for_all_checks' changedetectionio/worker_pool.py changedetectionio/tests/util.py` → per-file lines: sum `2` (one def each; run per-file to avoid multi-file count traps).
**Direct test:** Used by nearly every integration test via `tests/util.py:wait_for_all_checks(client)` delegating to this function with timeout=150 — e.g. `test_queue_handler.py:test_queue_system` relies on it before asserting idle.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-changedetection.io", query: "wait_for_all_checks queue empty workers idle", limit: 5 });
// → ext-changedetection.io.changedetectionio.worker_pool.wait_for_all_checks Function worker_pool.py 519-565
```

## Verdict
Adopt the two-signal + stability-window quiescence check for any queue+pool system's tests/shutdown. Adapt timeouts. Omit the fs-buffer sleep if your jobs have no disk writes.
