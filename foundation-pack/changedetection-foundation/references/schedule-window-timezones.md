<!-- capsule-v2 -->
# Timezone-pinned schedule windows — how does a daily HH:MM+duration window survive midnight and DST?

**Source:** changedetection.io Apache-2.0 `master@fce24780`; Codebase Memory `ext-changedetection.io`. **Question:** How is "is now inside this weekday's check window" evaluated so day boundaries are computed in the schedule's timezone, not the server's?

## Connected graph-selected seam
**Path/Symbol:** `changedetectionio/time_handler.py:am_i_inside_time` (:17-80), `is_within_schedule` (:83-116); direct unit tests `tests/unit/test_time_handler.py`.
**Signature:** `am_i_inside_time(day_of_week: str, time_str: str, timezone_str: str, duration: int = 15) -> bool`; `is_within_schedule(time_schedule_limit: dict, default_tz: str = 'UTC') -> bool`.
**Data Shape:** Schedule dict keyed by lowercase weekday name (`'monday'...`), each `{enabled, start_time 'HH:MM', duration {hours, minutes}}`, plus optional `timezone`. Duration collapses to minutes: `int(hours)*60 + int(minutes)`.

### Decisive source
```python
now_tz = arrow.now(timezone_str.strip())
current_weekday = now_tz.weekday()
start_datetime_tz = now_tz.replace(hour=hour, minute=minute, second=0, microsecond=0)

# Handle previous day's overlap
if target_weekday == (current_weekday - 1) % 7:
    start_datetime_tz = start_datetime_tz.shift(days=-1)
    end_datetime_tz = start_datetime_tz.shift(minutes=duration)
    if start_datetime_tz <= now_tz <= end_datetime_tz:
        return True
# Handle current day's range
if target_weekday == current_weekday:
    end_datetime_tz = start_datetime_tz.shift(minutes=duration)
    if start_datetime_tz <= now_tz <= end_datetime_tz:
        return True
# Handle next day's overlap
if target_weekday == (current_weekday + 1) % 7:
    end_datetime_tz = start_datetime_tz.shift(minutes=duration)
    if now_tz < start_datetime_tz and now_tz.shift(days=1) <= end_datetime_tz:
        return True
```

**Flow:** `is_within_schedule` resolves tz (schedule-level else default), formats TODAY'S name IN THAT TZ (`arrow.now(tz).format('dddd')`) to pick the day entry — the day itself is tz-relative — then delegates to `am_i_inside_time` which checks three arms: yesterday's window spilling forward, today's plain window (inclusive both ends), and tomorrow-today edge. All arithmetic in arrow/tz-aware space; no manual UTC offsets.
**Invariant:** The weekday is selected by formatting current time in the TARGET timezone — computing the weekday on server-local time then converting is the classic wrong port that shifts windows across DST/day boundaries. Inclusive `<=` on both ends means duration is window length; a 24h/0m config covers the whole day.
**Probe:** `grep -c "(current_weekday - 1) % 7" changedetectionio/time_handler.py` → `1`; per-term counts: `grep -c "arrow.now" changedetectionio/time_handler.py` → `2`; `grep -c "shift(days=-1)" changedetectionio/time_handler.py` → `1`; `grep -c "shift(days=1)" changedetectionio/time_handler.py` → `1`.
**Direct test:** `changedetectionio/tests/unit/test_time_handler.py::TestAmIInsideTime` (within/outside/Pacific/Tokyo/midnight-crossing arms) + integration `tests/test_scheduler.py:test_check_basic_scheduler_functionality` using Pacific/Kiritimati UTC+14.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-changedetection.io", query: "is_within_schedule time_schedule_limit", limit: 5 });
// → time_handler.is_within_schedule Function time_handler.py 83-116 + ticker caller flask_app.py
```

## Verdict
Adopt the three-arm inclusive-window algorithm wholesale for any daily schedule gate. Adapt storage schema of the schedule dict. Omit nothing — dropping any arm breaks midnight-spilling windows.
