<!-- capsule-v2 -->
# Optimizer step pipeline — which business-logic rewrites run, in what order, before SQL exists?

**Source:** Plausible Analytics AGPL-3.0 `master@9cc669b9`; Codebase Memory `ext-analytics`. **Question:** A porter must reproduce the exact pre-SQL query rewrite order — what are the steps and which ones silently drop metrics or mutate filters?

## Fixed-order reduce pipeline
**Path/Symbol:** `lib/plausible/stats/query_optimizer.ex:pipeline` (:52-64), `optimize/1` (:32-34), `split/1` (:43-50).
**Signature:** `optimize(query) :: Enum.reduce(pipeline(), query, fn step, acc -> step.(acc) end)` — each step is a captured `&step/1` on `%Query{}`.
**Data Shape:** Steps: `update_group_by_time` → `add_missing_order_by` → `update_time_in_order_by` → `extend_hostname_filters_to_visit` → `set_time_on_page_data` → `remove_time_on_page_if_unavailable` → `remove_revenue_metrics_if_unavailable` (EE only) → `trim_relative_date_range` → `set_sql_join_type`.

### Decisive source
```elixir
defp resolve_time_dimension(first, last) do
  cond do
    DateTime.diff(last, first, :hour) <= 48  -> "time:hour"
    DateTime.diff(last, first, :day)  <= 40  -> "time:day"
    Plausible.Times.diff(last, first, :week) <= 52 -> "time:week"
    true -> "time:month"
  end
end
```

**Flow:** bare `"time"` dimension resolves by range length; missing `order_by` defaults to `[{time_dim, :asc}, {hd(metrics), :desc}]` (no time dim: first metric desc); `set_sql_join_type` forces `sql_join_type: :full` **only** for `time:minute`/`time:hour`.
**Invariant:** (1) Order matters: hostname-filter extension must see dimensions *after* time resolution but *before* split; (2) metric-dropping steps (`remove_*_if_unavailable`) are gated behind explicit `include.drop_unavailable_*` opt-ins — a porter who drops unconditionally changes API results; (3) `trim_relative_date_range` fires only when the input range exactly equals the current month/year/day boundary (`should_trim_date_range?`) — trimming is label hygiene for graphs, not general clamping.
**Probe:** `test/plausible/stats/query/query_optimizer_test.exs:125` ("updates filters it filtering by event:hostname and visit:referrer and visit:exit_page dimensions") pins the appended-visit-hostname-filter order byte-for-byte.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^optimize$", fields: ["lines"], limit: 5 });
```

## Split: one query becomes per-table queries with renames
**Path/Symbol:** `lib/plausible/stats/query_optimizer.ex:split` (:43-50), `build_split_query(:sessions, ...)` (:177-198).
**Signature:** `split(query) :: [{table_type(), %Query{}}]` via `TableDecider.partition_metrics`.
**Data Shape:** Sessions-side renames map `"event:page" => "visit:entry_page"` and `"event:hostname" => "visit:entry_page_hostname"`; filters are renamed in lockstep through `Filters.rename_dimensions_used_in_filter/2`; `:sessions_smeared` adds `smear_session_metrics: true`.
**Flow:** partition metrics → per table_type build sub-query → sessions copy carries renamed dimensions+filters so the same breakdown can be computed from the sessions table.
**Invariant:** The rename table is load-bearing for the join later (`SQL.QueryBuilder.join_query_results` matches rows by identical shortnames). Forgetting `Filters.rename_dimensions_used_in_filter` produces silently-empty session results.
**Probe:** `grep -c 'build_split_query' lib/plausible/stats/query_optimizer.ex` → 4 (:162/:177/:200 + def split call site :48).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^build_split_query$", fields: ["lines"], limit: 5 });
```

## Verdict
Adopt the ordered-pipeline + split-with-rename architecture; adapt threshold numbers (48h/40d/52w) to product needs; omit EE revenue gating when porting CE.
