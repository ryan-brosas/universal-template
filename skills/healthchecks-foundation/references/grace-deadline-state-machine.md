<!-- capsule-v2 -->
# Grace-deadline state machine — when exactly does a dead man's switch flip to "down"?

**Source:** healthchecks BSD-3-Clause `master@29b5ec251059034b79e0120e2ff0c3e35d7bd9f8`; Codebase Memory `healthchecks`. **Question:** How does a check derive "when am I next expected" and "when do I go down" across simple/cron/OnCalendar kinds, and what does a porter get wrong around timezones?

## Check.get_grace_start / going_down_after / get_status
**Path/Symbol:** `hc/api/models.py:Check.get_grace_start` (:299-336), `going_down_after` (:338-348), `get_status` (:354-379).
**Signature:** `get_grace_start(*, with_started: bool = True) -> datetime | None`; `going_down_after() -> datetime | None`; `get_status(*, with_started: bool = False) -> str`.
**Data Shape:** Fields: `kind ∈ {simple, cron, oncalendar}`, `timeout: timedelta`, `grace: timedelta`, `schedule: str`, `tz: str`, `status ∈ {new, up, down, paused}`, `last_ping`, `last_start`, denormalized `alert_after` (persisted index for the scheduler). Module constant `NEVER = datetime(3000, 1, 1, tzinfo=utc)` is the sentinel for "no next elapse" — chosen over None so the min() ladder stays simple.

### Decisive source
```python
# hc/api/models.py — cron case of get_grace_start
last_local = self.last_ping.astimezone(ZoneInfo(self.tz))
result = next(CronSim(self.schedule, last_local))
# Important: convert from the local timezone back to UTC.
# If the result is kept in the local timezone, adding
# a timedelta to it later (in `going_down_after` and in `get_status`)
# may yield incorrect results during DST transitions.
result = result.astimezone(timezone.utc)
...
# oncalendar case can have NO future occurrence:
except StopIteration:
    result = NEVER
...
if with_started and self.last_start and self.status != "down":
    result = min(result, self.last_start)
return result if result != NEVER else None
```

**Flow:** `grace_start = last_ping + timeout` (simple) or `next(CronSim(schedule, last_ping_local)).astimezone(utc)` (cron) or `next(OnCalendar(...))` with StopIteration→NEVER (oncalendar); a running `last_start` participates via `min()` (a job running past its deadline is late NOW). Then `going_down_after() = grace_start + grace`. `get_status` evaluates in priority order: `last_start + grace <= now → down`; stored terminal states (`new/paused/down`) pass through; then `now >= grace_end → down`, `now >= grace_start → grace`, else `up`.
**Invariant:** All arithmetic happens on timezone-aware UTC datetimes; local-time conversion exists ONLY inside cronsim/oncalendar's "next occurrence" computation and must convert back before any timedelta addition. The `min(result, last_start)` fold means an un-finished run shortens the effective deadline — dropping it makes long-running jobs immortal. OnCalendar schedules can legitimately never fire again (StopIteration), which must degrade to "stays up", not to "down".
**Probe:** `hc/api/tests/test_check_going_down_after.py::test_it_handles_up` (expected_aa = last_ping + td(days=1, hours=1)), `test_it_handles_paused_check` (None), `hc/api/tests/test_check_model.py::test_get_grace_start_returns_utc` (asserts `.tzinfo == timezone.utc` for Europe/Riga schedule) and `test_get_status_handles_autumn_dst_transition` (time-machine frozen at 2023-10-29T01:05, check must still be "up").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "going_down_after get_grace_start alert_after", limit: 10 });
```
Resolves line-exact: `hc/api/models.py` Check.get_grace_start :299-336.

## Verdict
Adopt the three-kind deadline derivation with the UTC-normalization rule and the NEVER-sentinel pattern, the min()-with-last_start fold, and the four-state display machine. Adapt kind names, DEFAULT_TIMEOUT/DEFAULT_GRACE values, and cronsim/oncalendar to your host's schedule engines. Omit the denormalized `alert_after` column only if you don't need a partial-index scan feed for a poller (see the sendalerts capsule).
