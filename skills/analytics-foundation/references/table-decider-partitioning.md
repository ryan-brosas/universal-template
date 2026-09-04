<!-- capsule-v2 -->
# TableDecider metric/dimension partitioning — which ClickHouse table answers which metric, and when do results join?

**Source:** Plausible Analytics AGPL-3.0 `master@9cc669b9`; Codebase Memory `ext-analytics`. **Question:** Given a mixed metrics+dimensions request, how does the engine decide between one-table queries and an events⋈sessions join — and why do visitors/visits sometimes move to the sessions table?

## Five-way partition closure
**Path/Symbol:** `lib/plausible/stats/table_decider.ex:partition_metrics` (:88-122), `metric_partitioner/2` (:147-178), `dimension_partitioner/2` (:180-188).
**Signature:** `partition_metrics(requested_metrics, query) :: [{:events | :sessions | :sessions_smeared, [metric()]}]` (empty-metric groups rejected at :121).
**Data Shape:** Partition buckets `%{event: [], session: [], either: [], other: [], sample_percent: []}`; decision inputs are *three* partitions — metrics, dimensions, **and dimensions-used-in-filters**.

### Decisive source
```elixir
cond do
  empty?(metrics.event) && empty?(filters.event) && empty?(dimensions.event) ->
    [sessions: metrics.session ++ metrics.either ++ metrics.sample_percent]
  ...
  true ->  # Default: prefer events
    [events: metrics.event ++ metrics.either ++ metrics.sample_percent,
     sessions: metrics.session ++ metrics.sample_percent]
end
|> Enum.flat_map(&smear_session_metrics(&1, query))
```

**Flow:** any session-partitioned dimension or filter dimension ⇒ events must join sessions (`events_join_sessions?/1`); any event-partitioned *filter* dimension ⇒ sessions joins events (`sessions_join_events?/1`); both clean ⇒ single-table query.
**Invariant:** (1) `:either` metrics ride whichever single table survives; in a two-table query they land on events only; (2) `sample_percent` is deliberately included on BOTH sides then deduped at join (`query.metrics -- [:sample_percent]` in `select_join_metrics`); (3) `:other` bucket (`total_visitors`) is computed at callsite, never inside table queries.
**Probe:** `test/plausible/stats/table_decider_test.exs:7-19` pins `events_join_sessions?` truth table; `:166` "smearable metrics" pins the split into `[:sessions, ...], [:sessions_smeared, [:visitors, :visits]]`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^partition_metrics$|^events_join_sessions\\?$|^sessions_join_events\\?$", fields: ["lines"], limit: 6 });
```

## Smearing rule: minute/hour buckets need session presence, not event presence
**Path/Symbol:** `lib/plausible/stats/table_decider.ex:smear_session_metrics` (:129-144) + comment block (:124-127).
**Signature:** fires only when `"time:minute" in dimensions or "time:hour" in dimensions` AND not filtering on `event:goal`; splits `@smearable_metrics [:visitors, :visits]` into a separate `:sessions_smeared` sub-query.
**Data Shape:** The smeared sub-query later gets `timeSlots(...)` row-expansion (see expression capsule) so a session counts in every bucket it was alive, even with zero events.
**Invariant:** A porter who keeps smeared and non-smeared session metrics in ONE query double-counts visitors. The smear gate's `event:goal` exclusion exists because goal filtering is event-level and would make "session active in bucket" ill-defined.
**Probe:** `grep -c 'sessions_smeared' lib/plausible/stats/table_decider.ex` → 2 (:137 defp smear tuple + :173 partitioner).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", qn_pattern: "table_decider$", fields: ["lines"], limit: 15 });
```

## Verdict
Adopt the three-input partition closure and the smearing gate verbatim; adapt metric lists to your schema; omit revenue metric special-casing when porting CE.
