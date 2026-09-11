<!-- capsule-v2 -->
# Notification gating: first-check baseline + consecutive-failure threshold — when is a "change" allowed to page the user?

**Source:** changedetection.io Apache-2.0 `master@fce24780`; Codebase Memory `ext-changedetection.io`. **Question:** Why do notifications require history_n >= 2, and how does the filter-failure notification counter actually behave?

## Connected graph-selected seam
**Path/Symbol:** `changedetectionio/worker.py` (:455, :593-596 history gates; :281-298 filter-failure ladder); `NotificationQueue.put` mute gate in `queue_handlers.py` (:454-470).
**Signature:** `if changed_detected and watch.history_n >= 1:` (LLM diff gate); `if watch.history_n >= 2:` (notification send); `send_content_changed_notification(uuid, notification_q, datastore)` coroutine.
**Data Shape:** `watch.history_n` = number of saved snapshots. Filter-failure state: `consecutive_filter_failures` int on watch + global `filter_failure_notification_threshold_attempts` setting.

### Decisive source
```python
# Only run AI intent/summary when there's a PREVIOUS snapshot to diff against.
# On the very first check history_n is 0 ... running the LLM here would summarise
# the whole page as if it just changed ... Mirrors the notification gate
# (which only fires at history_n >= 2).
if changed_detected and watch.history_n >= 1:
```
```python
c = watch.get('consecutive_filter_failures', 0)
c += 1
threshold = datastore.data['settings']['application'].get('filter_failure_notification_threshold_attempts', 0)
if c >= threshold:
    if not watch.get('notification_muted'):
        await send_filter_failure_notification(uuid, notification_q, datastore)
    c = 0          # RESET — next notification needs another full N consecutive failures
datastore.update_watch(uuid=uuid, update_obj={'consecutive_filter_failures': c})
```
```python
# Queue-side kill switch: all_muted drops items BEFORE they enter the queue
if self.datastore and self.datastore.data['settings']['application'].get('all_muted', False):
    return False
```

**Flow:** First successful check saves a baseline snapshot and NEVER notifies (nothing to diff against). From the second snapshot on, a detected change enqueues a content-changed notification unless watch-level muted or globally all_muted (enforced at queue put-time, not send-time). The failure-counter resets BOTH after firing at threshold AND implicitly whenever a clean check runs (success branch sets it to 0) — so it counts strictly-consecutive failures.
**Invariant:** Any new "notify about X" path must be reachable only at `history_n >= 2` (or explicitly handle baseline); counters that gate notifications must reset on both fire and success, else one flapping filter spams forever.
**Probe:** `grep -n 'history_n >= 2' changedetectionio/worker.py` → 2 lines (`:454` gate comment + `:593` send gate; assert with `grep -c` → `2`); `grep -c 'watch.history_n >= 1' changedetectionio/worker.py` → `1`; `grep -c 'all_muted' changedetectionio/queue_handlers.py` → `3` (:443 comment + put :459 + async_put :483).
**Direct test:** `tests/test_filter_failure_notification.py` pins threshold/reset behavior end-to-end; `tests/test_basic_socketio.py` covers realtime status signals around checks.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-changedetection.io", query: "send_content_changed_notification history_n", limit: 5 });
// → worker.send_content_changed_notification Function + notification_service callers
```

## Verdict
Adopt the baseline-then-notify rule for any diff-based alerting system. Adapt threshold semantics carefully: upstream's counter-reset-on-fire means period-N reminders, not one-shot alerts. Omit the LLM summary cache plumbing if you have no AI layer.
