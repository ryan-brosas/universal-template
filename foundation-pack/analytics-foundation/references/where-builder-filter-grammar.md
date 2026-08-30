<!-- capsule-v2 -->
# WhereBuilder filter grammar → ClickHouse SQL — table-scoped no-ops, has_done subqueries, and the redundant primary-key lower bound

**Source:** Plausible Analytics AGPL-3.0 `master@9cc669b9`; Codebase Memory `ext-analytics`. **Question:** How does one filter AST (`[:is, "visit:source", [...]]` etc.) compile correctly against BOTH events and sessions tables, and what keeps sample estimation honest?

## Recursive dynamic-expression compiler
**Path/Symbol:** `lib/plausible/stats/sql/where_builder.ex:build` (:59-65), `add_filter` clauses (:122-215).
**Signature:** `build(table :: :events | :sessions, query) :: Ecto.Query.DynamicExpr`; filters are nested tuples `[op, dimension, clauses, opts?]`.
**Data Shape:** combinators: `[:not, f]`, `[:and|:or, [fs]]`, `[:ignore_in_totals_query, f]` (transparent), behavioral `[:has_done|:has_not_done, f]`; leaf ops: is/is_not, contains/contains_not, matches/matches_not (+ `_wildcard` variants), custom-prop and visit-prop variants.

### Decisive source
```elixir
defp add_filter(_table, query, [:has_done, filter]) do
  condition = dynamic([], ^filter_site_time_range(:events, query) and ^add_filter(:events, query, filter))
  dynamic([t], t.session_id in subquery(from(e in "events_v2", where: ^condition, select: e.session_id)))
end
defp add_filter(:events, _query, [_, "visit:" <> key | _rest] = filter) do
  field_name = db_field_name(key)
  if Enum.member?(@sessions_only_visit_fields, field_name), do: true, else: filter_field(field_name, filter)
end
defp add_filter(:sessions, _query, [_, "event:" <> _ | _rest]), do: true   # cannot apply directly
```

**Flow:** base condition = site_id + time range; every filter AND-ed on. Cross-table dimensions degrade to literal `true` (no-op) on the wrong table — correctness comes from the OTHER sub-query filtering or the join.
**Invariant:** (1) The garbage-filter catch-all returns `false` ("No results are returned") rather than raising — fail-closed by design (:208-215); (2) entry/exit props exist only on the sessions table (entry_meta column) so the events branch hard-noops them.
**Probe:** `grep -n 'Unable to process garbage filter' lib/plausible/stats/sql/where_builder.ex` → :209; `grep -c 'true$' ` over add_filter no-op branches → 3 (:178/:206 + entry_props :177).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^add_filter$", fields: ["lines"], limit: 4 });
```

## Sessions time-range carries a deliberate redundant bound
**Path/Symbol:** `lib/plausible/stats/sql/where_builder.ex:filter_time_range(:sessions)` (:100-120).
**Signature:**
```elixir
s.start >= ^(NaiveDateTime.add(first_datetime, -7, :day)) and
  s.timestamp >= ^first_datetime and
  s.start <= ^last_datetime
```
**Data Shape:** comment-documented invariant: sessions primary key starts with `start`; without a `start >=` predicate the row-sample estimator counts the whole unbounded prefix and **overestimates the sample factor for large sites**.
**Flow:** active-session semantics = session overlapping range (`start ≤ last ∧ activity ≥ first`) — not containment; the −7-day slack covers max session duration while restoring an index-usable lower bound.
**Invariant:** Removing the "redundant" bound doesn't change results, only sampling accuracy — the worst kind of regression to notice. Any porter must keep a lower-bound predicate aligned with the table's primary key.
**Probe:** `grep -n 'sample factor' lib/plausible/stats/sql/where_builder.ex` → comments at :110-115.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", qn_pattern: "sql.where_builder$", fields: ["lines"], limit: 15 });
```

## Custom-prop "(none)" and no-ref sentinel handling
**Path/Symbol:** `filter_custom_prop` (:217-297), `db_field_val/2` + `contains_clause_no_ref` (:359-428).
**Flow:** `[:is, ..., clauses]` with "(none)" in clauses ⇒ `(has_key ∧ value∈clauses) ∨ ¬has_key`; `is_not` inverts per-row but still treats missing-key as its own case. `@no_ref "Direct / None"` display sentinel maps to empty-string DB values (`db_field_val(_, val)` when sentinel) and `contains "Direct"` additionally ORs `field = ""`.
**Invariant:** Sentinel strings live in FOUR modules (`expression`, `where_builder`, `imported/sql/expression`, `filter_suggestions`) and must stay in sync — changing "Direct / None" in one silently splits dashboards.
**Probe:** `grep -rn 'Direct / None' lib/plausible/stats | wc -l` → 4 files.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^filter_custom_prop$", fields: ["lines"], limit: 3 });
```

## Verdict
Adopt the table-scoped compile-with-no-op strategy and the primary-key lower-bound rule; adapt the filter tuple grammar to your API; omit EE-only shield/replay filters.
