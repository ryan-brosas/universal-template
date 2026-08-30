<!-- capsule-v2 -->
# timeSlots session smearing — expanding one session row into every minute/hour bucket it was alive

**Source:** Plausible Analytics AGPL-3.0 `master@9cc669b9`; Codebase Memory `ext-analytics`. **Question:** How does a single sessions row appear in multiple time buckets without fan-out joins per bucket — and why 15-minute sub-slots for hours?

## ARRAY JOIN over generated slot list
**Path/Symbol:** `lib/plausible/stats/sql/expression.ex:time_slots` macro (:30-50), `select_dimension(q, key, "time:hour", :sessions, query) when smear_session_metrics` (:117-133).
**Signature:**
```sql
timeSlots(
  toTimeZone(greatest(?, ?), ?),
  toUInt32(timeDiff(greatest(?, ?), least(?, ?))),
  toUInt32(?)
)
```
bound to `s.start`, query-first, timezone, s.start, query-first, `s.timestamp` (session end), query-last, period seconds.
**Data Shape:** ClickHouse `timeSlots(start, duration, step)` returns an array of DateTime; the Ecto `join(... time_slot in time_slots(...), on: true)` + implicit ARRAY JOIN semantics expand each session into N rows, one per slot.

### Decisive source
```elixir
# :TRICKY: ClickHouse timeSlots works off of unix epoch and is not
#   timezone-aware. This means that for e.g. Asia/Katmandu (GMT+5:45)
#   to work, we divide time into 15-minute buckets and later combine these
#   via toStartOfHour
q
|> join(:inner, [s], time_slot in time_slots(query, 15 * 60, first, last), ...)
|> select_merge_as([s, time_slot: time_slot], %{key => fragment("toStartOfHour(?)", time_slot)})
```

**Flow:** clamp session window to `[greatest(start, range_first), least(timestamp_end, range_last)]` → generate slots → inner-join-on-true explodes rows → group by formatted slot.
**Invariant:** (1) Both endpoints are clamped or sessions starting before/ending after the range leak extra buckets; (2) hour granularity uses **15-minute** slots because UTC-offset zones with fractional hours (GMT+5:45) would otherwise snap slots to wrong epoch boundaries — `toStartOfHour` reassembles them after; (3) smearing applies only when TableDecider created a `:sessions_smeared` query — regular queries must never hit this branch or visitors inflate.
**Probe:** `test/plausible/stats/query/query_test.exs:442` ("unique conversions are not smeared across all session minutes via timeSlots") pins that goal-filtered queries stay event-exact while others smear.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^select_dimension$", fields: ["lines"], limit: 8 });
```

## Timezone-aware bucketing ladder for non-smeared dimensions
**Path/Symbol:** `lib/plausible/stats/sql/expression.ex:select_dimension` (:52-162).
**Flow:** month/day/hour/minute all wrap `toTimeZone(timestamp, ^query.timezone)` before truncation; sessions-table variants additionally wrap `least(t.timestamp, ^last_datetime)` so late-ending sessions can't create future buckets; weeks use custom `weekstart_not_before(to_timezone(ts), ^date_range.first)` fragment so partial first weeks anchor to the range start instead of an arbitrary Monday.
**Invariant:** Bucketing happens in site-local time, not UTC — a porter who drops `toTimeZone` shifts daily graphs by the site offset. The `least(…, last)` guard exists only on sessions variants because events can't outlive their own timestamp filter but sessions rows can span past `last`.
**Probe:** `grep -c 'weekstart_not_before' lib/plausible/stats/sql/expression.ex` → 2 (:79/:90).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", file_pattern: "stats/sql/expression.ex", fields: ["lines"], limit: 30 });
```

## Verdict
Adopt clamped timeSlots expansion + fractional-hour sub-slotting; adapt slot sizes; omit the imported-data twin expressions (`lib/plausible/stats/imported/sql/expression.ex`) which mirror this ladder over import tables.
