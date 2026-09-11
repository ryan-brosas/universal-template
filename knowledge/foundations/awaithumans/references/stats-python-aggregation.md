<!-- capsule-v2 -->
# Stats Python-Side Aggregation — pull the window, group in code, zero-fill the axis

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What does a pragmatic analytics service look like before SQL GROUP BY earns its keep — and which numbers are windowed vs all-time?

## Two queries + pure-function buckets; completion rate over ALL-TIME terminal counts
**Path/Symbol:** `packages/python/awaithumans/server/services/stats_service.py` — scale docstring (:1-11), `get_task_stats` (:28-53), `_totals` (:59-66), `_window_rows` (:69-85), `_bucket_by_day` (:91-121), `_bucket_by_channel` (:124-133), `_avg_completion_seconds` (:136-153); route clamps `window_days ∈ [1, 365]` (`routes/stats.py:21-22`).
**Signature:** `get_task_stats(session, *, window_days: int = 30) -> TaskStats`.
**Data Shape:** `totals` = ALL-TIME status→count; `by_day/by_channel/avg_completion_seconds` = WINDOW-only; `completion_rate` = all-time completed ÷ all-time TERMINAL (None when no terminals yet, NOT 0).

### Decisive source
```python
# Completion rate uses totals (all-time), matching operator intent:
# "of tasks that ever finished, how many did a human actually complete".
terminal_count = sum(totals.get(s.value, 0) for s in TERMINAL_STATUSES_SET)
completed_count = totals.get(TaskStatus.COMPLETED.value, 0)
completion_rate: float | None = completed_count / terminal_count if terminal_count > 0 else None
...
for offset in range(window_days - 1, -1, -1):     # exactly window_days entries ending today
    d = (today - timedelta(days=offset)).isoformat()
    out.append(TaskStatsByDay(date=d, created=created.get(d, 0), completed=completed.get(d, 0)))
```
`_avg_completion_seconds` returns None when nothing completed "so the UI can render '—' rather than a misleading 0"; channel bucket maps missing channel to literal `"unknown"`.

**Flow:** now → two SELECTs (all-time status column; window's four columns incl `completed_via_channel`) → pure-Python Counter buckets → day axis zero-filled so charts render a clean axis on dead days → assemble schema. Docstring records the growth path: replace with a CTE (`SELECT DATE(created_at), COUNT(*) … GROUP BY 1`) when thousands/day stop fitting under ~50 ms.
**Invariant:** window vs all-time semantics are PER-METRIC and deliberate — collapsing them into one scope silently changes operator meaning; None ≠ 0 for both rate and average.
**Probe:** `packages/python/tests/stats/test_stats_service.py` (`test_completion_rate`:75, `test_by_day_zero_fills_window`:124, `test_by_channel_only_counts_completed`:172, `test_window_filters_old_rows`:209, `test_completion_rate_none_when_no_terminals`:237) — suite green at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "get_task_stats _bucket_by_day completion_rate TERMINAL_STATUSES_SET", limit: 4 });
```
Live rank-1/2 line-exact (:28-53, :91-121) plus the direct tests.

## Verdict
Adopt the dual-scope semantics and zero-fill axis; adapt to SQL-side aggregation once your volume demands it (the source names the CTE); omit by_channel only if you don't track completion channel.
