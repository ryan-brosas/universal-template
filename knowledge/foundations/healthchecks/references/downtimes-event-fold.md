<!-- capsule-v2 -->
# Downtime statistics replay — boundaries-and-flips event fold with UTC-subtraction discipline

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How do you compute per-month (or week/day) downtime counts and uptime percentages from an append-only flip log, correctly across DST and pre-creation months?

## downtimes_by_boundary / DowntimeRecorder / month_boundaries
**Path/Symbol:** `hc/api/models.py:downtimes_by_boundary` (:611-645), `DowntimeRecord`/`DowntimeRecorder` (:153-189), `hc/lib/date.py:month_boundaries/week_boundaries/day_boundaries/seconds_in_month` (:103-161).
**Signature:** `downtimes_by_boundary(boundaries: list[datetime], tz: str) -> list[DowntimeRecord]` (boundaries presorted DESCENDING); `downtimes(months: int, tz: str)` convenience; `monthly_uptime() -> float`.
**Data Shape:** Events list = `[(b, "---") for b in boundaries] + [(created, old_status) for flips after min(boundary)]`; walk carries `(dt, status)` starting from `(now(), self.status)`. `"---"` is the boundary marker sentinel that must NOT overwrite the carried status.

### Decisive source
```python
# hc/api/models.py — reverse chronological fold
dt, status = now(), self.status
for prev_dt, prev_status in sorted(events, reverse=True):
    if status == "down":
        # Before subtracting datetimes convert them to UTC.
        # Otherwise we will get incorrect results around DST transitions:
        delta = dt.astimezone(timezone.utc) - prev_dt.astimezone(timezone.utc)
        summary.add(prev_dt, delta)
    dt = prev_dt
    if prev_status != "---":
        status = prev_status

# hc/lib/date.py — month length that knows DST:
def seconds_in_month(d, tzstr):
    start_utc = datetime(d.year, d.month, 1, tzinfo=tz).astimezone(timezone.utc)
    ...  # next month 1st, same tz
    return (end_utc - start_utc).total_seconds()
```

**Flow:** Caller asks for N periods in the account's tz; Profile.send_report uses 3 boundaries then discards the current one (`past_downtimes = downtimes[:-1]`) so reports cover CLOSED periods only. The fold walks flips newest→oldest attributing each down-interval to the boundary it started in; DowntimeRecorder routes durations to records and flags `no_data=True` for intervals before check.created. monthly_uptime divides by real calendar seconds (31-day March ≠ 30-day April; Europe/Riga October has +1h).
**Invariant:** Subtract aware datetimes only after forcing BOTH to UTC — Python subtracts wall-clock fields within a tz, which mis-measures every interval crossing a DST jump (upstream comment says this verbatim; tests pin it with time_machine at the autumn transition). The `"---"` guard is what lets boundaries participate in ordering without mutating status interpretation. Flip retention (~93 days, see prune capsule) is what makes "current + two full previous months" computable — statistics and retention are coupled contracts.
**Probe:** `hc/api/tests/test_check_model.py::test_downtimes_handles_flip_two_months_ago` (jan duration td(days=14), nov monthly_uptime()==14/30), `test_monthly_uptime_pct_handles_dst`, `test_downtimes_handles_non_utc_timezone`, `test_downtimes_handles_months_when_check_did_not_exist` (no_data flags), `hc/lib/tests/test_date.py::SecondsInMonthTestCase::test_it_handles_dst_extra_hour` (+3600s).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "downtimes boundaries flip summary utc", limit: 10 });
```
Resolves line-exact: downtimes_by_boundary :611-645.

## Verdict
Adopt the descending event-fold with marker sentinels, force-UTC subtraction rule, no_data semantics for pre-existence intervals, and closed-period report windows. Adapt period lengths and the tz source (account vs project). Omit weekly/day variants freely — they fall out of swapping the boundary generator.
