<!-- capsule-v2 -->
# QueryRunner comparison shapes — how do main and comparison results get assembled without double-querying?

**Source:** Plausible Analytics AGPL-3.0 `master@9cc669b9`; Codebase Memory `ext-analytics`. **Question:** When a query carries `include.compare`, where does the comparison execute relative to the main query, and why do timeseries and dimensional breakdowns return comparison data in two different shapes?

## Optimized-run pipeline struct
**Path/Symbol:** `lib/plausible/stats/query_runner.ex:run` (:37-48), `build_results_list` (:108-128).
**Signature:** `run(site, query) :: %Plausible.Stats.QueryResult{}` — internal `%__MODULE__{site, main_query, main_results, comparison_query, comparison_results, total_rows, results}` threaded through function-composition pipe.
**Data Shape:** `query.include.compare` ∈ `nil | :previous_period | :year_over_year | {:date_range|:datetime_range, from, to}`; rows are `%{dimensions: [label], metrics: [value]}` lists.

### Decisive source
```elixir
case {query.include.compare, query.dimensions} do
  {nil, _dimensions} -> ...results: main_results, comparison_results: nil
  {_non_nil_compare, ["time:" <> _]} ->
    ...results: main_results, comparison_results: build_comparison_results(runner)
  {_non_nil_compare, _dimensions} ->
    ...results: merge_with_comparison_results(main_results, runner), comparison_results: nil
end
```

**Flow:** optimize → trace → execute main → (compare? build comparison_query = Comparisons.get_comparison_query + **add_comparison_filters(main_results)** + re-optimize) → execute comparison → shape by `{compare, dimensions}`.
**Invariant:** The comparison query is filtered to the *main query's resulting dimension values* (`Comparisons.add_comparison_filters`, wrapped in `[:ignore_in_totals_query, ...]`, pagination dropped) so every merged comparison row is guaranteed a matching main row. Timeseries keeps two parallel lists joined by label-zip (`Time.time_labels(comparison) ↔ Time.time_labels(main)`); dimensional merges inline as `row.comparison = %{dimensions, metrics, change}`. Missing pairs get `Compare.calculate_change(metric, comp_value, nil)` semantics / default metrics — never crashes.
**Probe:** `test/plausible/stats/query/query_comparisons_test.exs:34` ("timeseries comparison") and `:154` ("dimensional comparison with low limit") pin both shapes end-to-end through ClickHouse.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^build_comparison_results$|^add_comparison_results$", limit: 5 });
```

## Goal dimension decodes by index, not string
**Path/Symbol:** `lib/plausible/stats/query_runner.ex:get_dimension_goal` (:210-215).
**Signature:** `query.preloaded_goals.matching_toplevel_filters |> Enum.at(goal_index - 1)` where `goal_index` came from the SQL `event_goal_join` fragment.
**Data Shape:** ClickHouse returns the 1-based position into the goal arrays baked at build time; the runner maps it back to a `%Plausible.Goal{}` for `display_name/1`.
**Flow:** SQL emits index → runner resolves `Enum.at(goals, idx-1)` → display name becomes the dimension label.
**Invariant:** Any porter who changes goal array ordering in `Goals.goal_join_data/1` breaks decoding silently — ordering must stay identical between SQL emission and `preloaded_goals.matching_toplevel_filters`.
**Probe:** `grep -n 'Enum.at(goal_index - 1)' lib/plausible/stats/query_runner.ex` → exactly 1 match (:214).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", qn_pattern: "stats.query_runner$", fields: ["lines"], limit: 20 });
```

## Verdict
Adopt the two-shape comparison contract and the index-decode invariant wholesale; adapt `[:ignore_in_totals_query, ...]` marker to your own filter grammar; omit Plausible's `on_ee` revenue branches when porting CE-only.
