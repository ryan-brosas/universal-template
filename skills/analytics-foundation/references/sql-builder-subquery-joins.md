<!-- capsule-v2 -->
# SQL.QueryBuilder subquery-join assembly — how do per-table queries become one result set with correct pagination and total_rows?

**Source:** Plausible Analytics AGPL-3.0 `master@9cc669b9`; Codebase Memory `ext-analytics`. **Question:** After splitting into events/sessions queries, how are they recombined — where do LIMIT/OFFSET apply, and why is `count() over ()` used for totals?

## Build pipeline over Ecto queries
**Path/Symbol:** `lib/plausible/stats/sql/query_builder.ex:build` (:17-28), `join_query_results` (:232-246), `paginate` (:251-255), `select_total_rows` (:259-262).
**Signature:** `build(query, site) :: Ecto.Query.t()` = split → per-table build → join → order_by → paginate → total_rows.
**Data Shape:** Per-table stage wraps `from(e in "events_v2"|"sessions_v2")` with `^SQL.WhereBuilder.build/2`, metric selects via `Expression.event_metric/session_metric`, then composes joins/group-bys/imported-merge/special-metrics.

### Decisive source
```elixir
defp select_total_rows(q, true = _include_total_rows) do
  q |> select_merge([], %{total_rows: fragment("count() over ()")})
end
```

**Flow:** each table query becomes a **subquery**; the FIRST becomes the outer `from(e in subquery(q))`; later ones attach via `join(acc, main_query.sql_join_type, [], s in subquery(q), on: ^build_group_by_join(main_query))` — equality on every dimension shortname, or literal `true` when dimensions are empty.
**Invariant:** (1) Pagination applies to the JOINED result, not per-table — a porter paginating inside a subquery gets wrong pages; (2) `total_rows` uses ClickHouse window function `count() over ()` so the pre-pagination count rides every row (`QueryRunner.total_rows([first_row | _])` just reads it); (3) legacy queries pass `pagination: nil` and do their own (:249).
**Probe:** `grep -c 'count() over ()' lib/plausible/stats/sql/query_builder.ex` → 1; `grep -n 'defp paginate' ...` → :251.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^join_query_results$|^select_total_rows$", fields: ["lines"], limit: 5 });
```

## Conditional session/event joins carry their own WHERE
**Path/Symbol:** `lib/plausible/stats/sql/query_builder.ex:join_sessions_if_needed` (:74-107) / `join_events_if_needed` (:109-132).
**Signature:** sessions side: `select: %{session_id: s.session_id}, group_by: s.session_id` + `where: s.sign == 1`; events side: `session_id: fragment("DISTINCT ?", e.session_id)` + `_sample_factor`.
**Data Shape:** Session-only dimensions get explicitly selected into the joined subquery through `Expression.select_dimension_internal/2` (`any(entry_page)`, but exit page uses `argMax(exit_page, events)` because exit changes during the session).
**Flow:** join condition is bare `e.session_id == sq.session_id` — no dimension equality needed at this level because group-level joining happens later in `join_query_results`.
**Invariant:** The `sign == 1` / `DISTINCT` asymmetry encodes CollapsingMergeTree semantics: sessions rows cancel in pairs, events must dedupe to one row per session before joining or metrics multiply.
**Probe:** `grep -c 'argMax' lib/plausible/stats/sql/expression.ex` → 2 (:269/:276 exit_page + exit_page_hostname).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", qn_pattern: "sql.query_builder$", fields: ["lines"], limit: 20 });
```

## Dimension provenance: leftmost vs rightmost table
**Path/Symbol:** `lib/plausible/stats/sql/query_builder.ex:select_from` (:299-309).
**Flow:** `sql_join_type == :left` ⇒ leftmost; smeared `time:minute|time:hour` ⇒ **rightmost** (the sessions subquery owns bucket presence); default ⇒ leftmost.
**Invariant:** Picking the wrong side for smeared time buckets resurrects empty buckets that have no session alive — the exact bug smearing exists to prevent.
**Probe:** `test/plausible/stats/query/query_test.exs:95` ("visitors and visits are smeared across time:minute buckets but visit_duration is not") pins full bucket-by-bucket output including zero-event minutes.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^select_from$", fields: ["lines"], limit: 3 });
```

## Verdict
Adopt subquery-join composition + windowed total_rows; adapt shortname mechanics to your SQL toolkit; omit imported-data merge hooks (`merge_imported`) if you have no imports plane.
