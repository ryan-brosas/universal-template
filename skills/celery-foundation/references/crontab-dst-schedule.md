<!-- capsule-v2 -->
# Crontab DST-safe schedule math — how do you compute "next run" for cron fields without timezone bugs?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** How does crontab.remaining_delta normalize timezones and walk field sets forward, and what does is_due's starting-deadline loop protect against?

## crontab.remaining_delta / is_due
**Path/Symbol:** `celery/schedules.py:crontab.remaining_delta` (:580-643), `remaining_estimate` (:644), `is_due` (:655-702); simple-interval twin `schedule.is_due` (:146-176); field expansion `_expand_cronspec`.
**Signature:** `remaining_delta(last_run_at, tz=None, ffwd=ffwd) -> (last_run_at, delta, now)`; `is_due(last_run_at) -> schedstate(is_due: bool, next: seconds)`; config knob `beat_cron_starting_deadline` (seconds or None).
**Data Shape:** expanded field SETS `minute(60)/hour(24)/day_of_week(7, Sunday=0)/day_of_month(31-based 1..31)/month_of_year(12)`; original patterns kept on `_orig_*` for the all-wildcard fast path.

### Decisive source
```python
# celery/schedules.py:588-596 — normalize BOTH clocks into schedule tz
schedule_tz = timezone.get_timezone(tz or self.tz)
# Normalize both datetimes into the schedule's timezone ... An aware
# last_run_at may arrive in a different timezone (e.g. django-celery-beat).
last_run_at = self.maybe_make_aware(last_run_at).astimezone(schedule_tz)
now = self.maybe_make_aware(self.now()).astimezone(schedule_tz)
dow_num = last_run_at.isoweekday() % 7      # Sunday is day 0, not day 7
```
```python
# :655-699 — due decision + missed-run deadline walk
rem_delta = self.remaining_estimate(last_run_at)
due = max(rem_delta.total_seconds(), 0) == 0
if deadline_secs is not None:
    while rem_secs < 0:
        last_date_checked = last_date_checked + abs(rem_delta)
        rem_delta = self.remaining_estimate(last_date_checked)
        if rem_secs < 0:
            last_feasible_rem_secs = rem_secs   # keep LAST feasible run
    has_passed_deadline = -last_feasible_rem_secs > deadline_secs
    if has_passed_deadline:
        due = False                              # too stale: skip, don't burst
if due or has_passed_deadline:
    rem_delta = self.remaining_estimate(self.now())   # re-anchor to NOW
```

**Flow:** next-match ladder: same-hour later minute → later hour today → next matching weekday (all-dom/moy fast path adds whole weeks via ffwd(weeks=add_week)) → `_delta_to_next` for mixed day/month fields → is_due subtracts; when due (or deadline-expired) it recomputes remaining FROM NOW so the returned `next` is a clean full interval. Simple `schedule.is_due` clamps negative remaining to 0 and returns `(True, run_every_seconds)`.
**Invariant:** (1) Both operands must be normalized INTO the schedule's tz before field matching — comparing aware datetimes across zones gives correct arithmetic but WRONG wall-clock fields. (2) Sunday=0 via `isoweekday()%7` (ISO makes it 7). (3) After firing, `next` is measured from now, not from last_run_at — otherwise intervals drift by execution delay. (4) Starting-deadline turns catch-up bursts into skips: only runs missed within N seconds fire. (5) The comment block warns DST addition must happen on UTC-normalized datetimes.
**Probe:** `t/unit/app/test_schedules.py::test_day_after_dst_end` (:498), `test_day_after_dst_start` (:515), `class test_crontab_is_due::test_every_minute_execution_is_due` (:726); beat-side `t/unit/app/test_beat.py` heap integration.
**Retrieve:**
```json
{"project":"ext-celery","query":"crontab remaining_delta is_due beat_cron_starting_deadline","limit":5,"detail":"ids"}
```
## Verdict
Adopt: dual-tz normalization, modulo-7 weekday, re-anchor-on-fire, and the optional missed-run deadline walk. Adapt ffwd/dateutil to your calendar lib; keep the wildcard fast path if schedules are hot-path evaluated. Omit solar schedules unless you need sunrise/sunset triggers.
