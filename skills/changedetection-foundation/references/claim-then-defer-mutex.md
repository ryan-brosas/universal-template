<!-- capsule-v2 -->
# Claim-then-defer UUID mutex — how do N workers share one queue without double-fetching a watch?

**Source:** changedetection.io Apache-2.0 `master@fce24780`; Codebase Memory `ext-changedetection.io`. **Question:** Where exactly must the per-UUID mutual-exclusion check happen so the same watch is never fetched twice concurrently?

## Connected graph-selected seam
**Path/Symbol:** `changedetectionio/worker.py:async_update_worker` (:90-100); `changedetectionio/worker_pool.py:claim_uuid_for_processing` (:285-309), `release_uuid_from_processing` (:312-327), module globals :18-23.
**Signature:** `claim_uuid_for_processing(uuid, worker_id) -> bool`; `release_uuid_from_processing(uuid, worker_id) -> None` (owner-checked); state = `{uuid: worker_id}` + `{uuid: started_at}` under one `threading.Lock`.
**Data Shape:** Module-level dicts `currently_processing_uuids`, `_uuid_started_at` protected by `_uuid_processing_lock`. Claim is check-and-set inside a single lock hold.

### Decisive source
```python
# CRITICAL: Claim UUID immediately after getting from queue to prevent race condition
# in wait_for_all_checks() which checks qsize() and running_uuids separately
uuid = queued_item_data.item.get('uuid')
if not worker_pool.claim_uuid_for_processing(uuid, worker_id):
    # Already being processed - re-queue and continue
    await asyncio.sleep(DEFER_SLEEP_TIME_ALREADY_QUEUED)
    deferred_priority = max(1000, queued_item_data.priority * 10)
    deferred_item = PrioritizedItem(priority=deferred_priority, item=queued_item_data.item)
    worker_pool.queue_item_async_safe(q, deferred_item, silent=True)
    continue
```
```python
with _uuid_processing_lock:
    if uuid in currently_processing_uuids:
        return False          # someone else owns it
    currently_processing_uuids[uuid] = worker_id   # atomic claim
    _uuid_started_at[uuid] = _t.time()
    return True
```

**Flow:** pop from queue → IMMEDIATELY claim (before any fetch work) → if lost the race: sleep (`0.3s` pytest / `10.0s` prod via `DEFER_SLEEP_TIME_ALREADY_QUEUED`) → re-queue same payload at demoted priority `max(1000, p*10)` → continue loop. Release happens in the worker's `finally`, AFTER finalize hooks complete, so `wait_for_all_checks()` (which polls qsize==0 AND no running uuids) cannot report idle while plugin hooks still run.
**Invariant:** The dedup point is BETWEEN dequeue and work — never at enqueue time (the ticker's `uuid in running/queued` checks are advisory only and race by design). Ownership release is defensive: only the claiming worker_id can remove its entry.
**Probe:** `grep -c 'claim_uuid_for_processing' changedetectionio/worker.py` → `1` (:93 — the call; the :142 comment paraphrases without naming it); `grep -cF "doesn't own it" changedetectionio/worker_pool.py` → `1`; `grep -c 'DEFER_SLEEP_TIME_ALREADY_QUEUED' changedetectionio/worker.py` → `2` (:28 def + :96 use).
**Direct test:** `changedetectionio/tests/test_queue_handler.py:test_queue_system` final assertion `len(running_uuids) == 0` after wait proves every claimed UUID is released even across concurrent processing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-changedetection.io", query: "claim_uuid_for_processing atomic", limit: 5 });
// CLI trace (6 callers incl tests): codebase-memory-mcp cli trace_path '{"project":"ext-changedetection.io","function_name":"claim_uuid_for_processing","direction":"both","depth":2,"include_tests":true}'
// → callers: async_update_worker, start_single_async_worker(hop 2), 4 queue_ui tests
```

## Verdict
Adopt claim-at-dequeue with priority-demotion deferral for any multi-worker queue over keyed jobs. Adapt the defer sleep to your test/prod split via an env-visible constant. Omit nothing here — the release-after-finalize ordering is load-bearing for graceful-shutdown tests.
