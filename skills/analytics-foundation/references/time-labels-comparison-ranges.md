<!-- capsule-v2 -->
# Time labels & comparison range arithmetic — client-side bucket scaffolding and period shifting

**Source:** Plausible Analytics AGPL-3.0 `master@9cc669b9`; Codebase Memory `ext-analytics`. **Question:** How does the API promise a dense bucket axis (including empty buckets) and correct previous-period/year-over-year ranges across timezones and leap years?

## Label generation per granularity
**Path/Symbol:** `lib/plausible/stats/time.ex:time_labels` (:49-122), `partial_time_labels` (:124-154), `present_index` (:196-223).
**Signature:** `time_labels(query) :: [String.t()]` — month walks from `beginning_of_month(last)` BACKWARDS (`n..0//-1`), week anchors `date_or_weekstart`, hour/minute iterate naive steps; `time:minute` additionally stops at `min(range_end, now)` so future minutes never appear.
**Data Shape:** Labels are display strings (`%Y-%m-%d %H:%M:%S`) that double as join keys: QueryRunner zips `comparison ↔ main` label lists positionally, and `time_label_result_indices` meta maps labels→row indices.
**Flow:** generated in site timezone via `DateTimeRange.to_timezone(utc_time_range, query.timezone)` before stepping.
**Invariant:** (1) Month labels anchor on the LAST bucket's month-start (not first) because the first bucket may be partial — walking backwards keeps full months aligned; (2) `partial_time_labels/2` returns only edge buckets whose start/end crosses `now` or range bounds — the dashboard dims exactly those; (3) `present_index/2` finds "today" by formatting now in the same grammar as labels — any format drift breaks the highlight silently.
**Probe:** `test/plausible/stats/time_test.exs:9` describe "partial_time_labels/2" (19 matches for partial/present in file).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^partial_time_labels$|^time_labels$", fields: ["lines"], limit: 6 });
```

## Comparison range ladder
**Path/Symbol:** `lib/plausible/stats/comparisons.ex:get_comparison_utc_time_range` (:50-72), datetime vs date split (:74-83), `shift_to_nearest` (:241-250).
**Signature:** modes `:previous_period` (shift back own length), `:year_over_year` (−1y), custom date/datetime range; option `compare_match_day_of_week` snaps start to nearest matching weekday EXCLUDING the original date (`reject` arg).
**Data Shape:** 24h/today periods shift DATETIMES directly (hour −24 / day −7 / year −1) to preserve intra-day precision; older periods shift DATES then rebuild DateTimeRange in query timezone.
### Decisive source
```elixir
defp previous_period(source_date_range = %{first: f, last: l}) do
  diff_in_days = Date.diff(f, l) - 1        # NOTE: minus one
  new_first = Date.add(f, diff_in_days)
  new_last  = Date.add(l, diff_in_days)
  ...
end
```
**Invariant:** (1) The `- 1` makes consecutive periods CONTIGUOUS (period length = diff+1 days); dropping it inserts an off-by-one gap — pinned by tests; (2) leap-year YoY uses `Date.shift(year: -1)` + explicit day-diff re-widening (:193-202) because calendar-year shifts change lengths; (3) `trim_trailing: true` on source range prevents comparing against not-yet-arrived future days.
**Probe:** `test/plausible/stats/comparisons_test.exs:110` ("shifts back whole month plus one day when mode is year_over_year and a leap year") + `:41` (day-of-week match when nearest day IS original start). Structural: `grep -n 'Date.diff(source_date_range.first, last) - 1' lib/plausible/stats/comparisons.ex` → exactly :208.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^get_comparison_date_range$|^shift_to_nearest$", fields: ["lines"], limit: 5 });
```

## Verdict
Adopt label-as-key scaffolding + contiguous-shift arithmetic; adapt granularity set; omit imported-data skip logic entangled with comparisons.
