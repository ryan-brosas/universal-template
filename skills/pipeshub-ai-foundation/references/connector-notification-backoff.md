<!-- capsule-v2 -->
# Notification backoff cache — how does a chatty connector avoid spamming users with the same failure alert every sync?

**Source:** PipesHub AI Apache-2.0 `main@c28d1336`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** Alerts for broken connectors must repeat eventually but not per-run — what's the dedupe/backoff shape and where does it live?

## Class-level key-cache with 1 h initial / 7 d max exponential backoff
**Path/Symbol:** `backend/python/app/connectors/core/base/connector_service.py:` `_notification_cache: dict[str, tuple[int,int]] = {}` (CLASS attribute — shared across instances), `INITIAL_NOTIFICATION_BACKOFF = 3600*1000` / `MAX_NOTIFICATION_BACKOFF = 604800*1000` (:26-27), `_suppress_notification` (:424-447), fire-and-forget `notify` wrapper (:360-423).
**Signature:** `def _suppress_notification(self, title, message, severity) -> bool`; cache value `(next_allowed_time_ms, current_backoff_ms)` keyed `f"{connector_id}:{title}:{message}"`.
**Data Shape:** INFO/SUCCESS severities bypass suppression entirely (always delivered).

### Decisive source
```python
if now - next_allowed_time > MAX_NOTIFICATION_BACKOFF:
    # Backoff expired after long silence → reset to initial backoff
    self._notification_cache[key] = (now + INITIAL_NOTIFICATION_BACKOFF, INITIAL_NOTIFICATION_BACKOFF)
else:
    new_backoff = min(backoff * 2, MAX_NOTIFICATION_BACKOFF)   # double up to 7 days
    self._notification_cache[key] = (now + new_backoff, new_backoff)
```

**Flow:** error-path notification → severity gate → cache probe → suppressed? log-and-drop : publish via broker as detached task (`_background_tasks` set + discard callback; RuntimeError when no loop ⇒ skip, keeping sync tests loop-free). First failure schedules retry in 1 h; each subsequent ALLOWED send doubles the gap capped at 7 days; a week of silence resets the ladder.
**Invariant:** Suppression applies only to WARN/ERROR-class alerts — success/info notifications are never throttled (users must see recoveries instantly). Cache is class-level because instances are rebuilt on re-auth while alert identity (connector+title+message) outlives them. Publishing is fire-and-forget so a broker outage can never fail a sync.
**Probe:** `grep -c 'MAX_NOTIFICATION_BACKOFF = 604800' app/connectors/core/base/connector/connector_service.py` → `1`; suite `tests/unit/connectors/core/test_connector_service.py` (17 tests) GREEN in battery.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "_suppress_notification backoff notification cache", limit: 3 });
```
**Verdict:** Adopt thresholds + reset-after-silence rule + class-level cache placement; adapt severity enum/broker call.
