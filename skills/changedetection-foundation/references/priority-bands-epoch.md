<!-- capsule-v2 -->
# Epoch-time priority encoding — how do immediate UI clicks jump ahead of thousands of scheduled jobs?

**Source:** changedetection.io Apache-2.0 `master@fce24780e74199bf34c62a0d90188cc2fc12f061`; Codebase Memory `ext-changedetection.io`. **Question:** What are the reserved priority values, who assigns them, and why does the scheduler encode wall-clock time as priority?

## Connected graph-selected seam
**Path/Symbol:** `changedetectionio/flask_app.py:ticker_thread_check_time_launch_checks` (:1344-1351); producers in `blueprint/ui/__init__.py`, `api/Watch.py`, `realtime/events.py`, `__init__.py`; labels in `blueprint/ui/queue.py:PRIORITY_LABELS` (:23-25).
**Signature:** Scheduler: `priority = int(time.time())` then `PrioritizedItem(priority=priority, item={'uuid': uuid})`. Interactive producers: `PrioritizedItem(priority=1, item={'uuid': uuid})`; clone flows use `priority=5`.
**Data Shape:** Priority is an int. Reserved bands: `1` = immediate/user/API/socket recheck-now; `5` = clone-created watches; `>100` = scheduler-enqueued (epoch seconds); deferred re-queues use `max(1000, original_priority * 10)`.

### Decisive source
```python
# Use Epoch time as priority, so we get a "sorted" PriorityQueue, but we can still push a priority 1 into it.
priority = int(time.time())
# Into the queue with you
queued_successfully = worker_pool.queue_item_async_safe(update_q,
                                                           queuedWatchMetaData.PrioritizedItem(priority=priority,
                                                                                               item={'uuid': uuid})
                                                           )
```
```python
PRIORITY_LABELS = {
    1: "immediate",
    5: "clone",
}
def _priority_label(priority):
    if priority in PRIORITY_LABELS:
        return PRIORITY_LABELS[priority]
    if priority > 100:
        return "scheduled"
    return f"p{priority}"
```

**Flow:** Ticker computes each watch's due-ness against threshold+jitter; when due it enqueues with `int(time.time())` as priority. Because min-heap pops smallest first, all interactive `priority=1` items drain before any scheduled item, and among scheduled items the OLDEST due-time wins (fairness by over-dueness). A job bounced because its UUID was already running gets re-prioritized to `max(1000, p*10)` so it cannot starve fresh work.
**Invariant:** Min-heap ordering + reserved low integers is the entire preemption mechanism — no separate express lane exists. Any new producer MUST pick from these bands or epoch time; using an arbitrary small int would jump the interactive queue.
**Probe:** `grep -rcF 'priority=1' changedetectionio/blueprint/ui/__init__.py` → `4` (lines 72, 316, 343, 369 — line 343 uses key `watch_uuid`); clone check: `grep -cF 'priority=5' changedetectionio/blueprint/ui/__init__.py` → `1`; scheduler epoch: `grep -c 'priority = int(time.time())' changedetectionio/flask_app.py` → `1`.
**Direct test:** `changedetectionio/tests/test_queue_ui.py:test_queue_state_full_lifecycle` asserts lifecycle through the queue page including label rendering; unit mirror in `blueprint/ui/queue.py` `_priority_label` mapping.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-changedetection.io", query: "_priority_label PRIORITY_LABELS immediate clone", limit: 5 });
// CLI: codebase-memory-mcp cli search_graph '{"project":"ext-changedetection.io","query":"_priority_label","limit":5,"detail":"ids"}'
// → changedetectionio.blueprint.ui.queue._priority_label Function blueprint/ui/queue.py 27-32
```

## Verdict
Adopt epoch-as-priority with small reserved ints for preemption — it converts a FIFO fairness problem into plain heap order. Adapt band numbers to your call sites but keep the ">100 = scheduled" reading convention consistent with any UI. Omit the queue-page label taxonomy if you expose no inspection UI.
