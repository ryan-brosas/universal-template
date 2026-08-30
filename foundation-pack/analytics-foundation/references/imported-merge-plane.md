<!-- capsule-v2 -->
# Imported-data merge plane — table routing, lossy paginate optimization, and weighted metric recombination

**Source:** Plausible Analytics AGPL-3.0 `master@9cc669b9` (`lib/plausible/stats/imported/*`); Codebase Memory `ext-analytics`. **Question:** How does a query combine native ClickHouse events with pre-aggregated Google-Analytics import tables without double counting or wrecking ratio metrics?

## Dimension→table routing closure
**Path/Symbol:** `lib/plausible/stats/imported/base.ex:decide_tables` (:79-95), `do_decide_tables` (:155-208), `@property_to_table_mappings` (:14-42).
**Signature:** returns list of import tables to merge (`[]` ⇒ no imported data); behavioral filters (`has_done`) force `[]` because aggregated imports cannot express event sequences.
**Data Shape:** mappings route visit dims → `imported_{sources,entry_pages,exit_pages,locations,devices,browsers,operating_systems}`, `event:page` → `imported_pages`, `event:name` → `imported_custom_events`; goal-dimension queries may need BOTH pages+custom_events.
**Flow:** `do_decide_tables` maps filter+dimension set through the mapping; candidates collapse to ONE table else abort to `[]` (ambiguity = skip imports); custom-prop queries have their own gated path requiring an exact event/goal-name top-level filter.
**Invariant:** The single-candidate collapse is the correctness core — merging two differently-shaped import tables would double-count visitors. Skip reasons surface to users via `Query.get_skip_imported_reason` (`:unsupported_query|:out_of_range|...`) and QueryResult meta warnings.
**Probe:** `grep -c 'defp do_decide_tables\|def decide_tables' lib/plausible/stats/imported/base.ex` → 5 (:77 def decide_tables + :152/:154/:158/:182 defp do_decide_tables heads).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^merge_imported$", fields: ["lines"], limit: 5 });
```

## Lossy top-N×100 join optimization
**Path/Symbol:** `lib/plausible/stats/imported/imported.ex:paginate_optimization` (:349-367) with design comment (:335-348).
**Signature:** when pagination is set AND order_by is deterministic (no `@cannot_optimize_metrics` like bounce_rate/conversion_rate), both native and imported subqueries are limited to `(limit + offset) * 100` rows before joining.
**Data Shape:** comment admits the trade-off verbatim: "lossy as the true top N values can arise from outside the top C items of either subquery. In practice though, this will give plausible results."
**Invariant:** This is an intentional approximation for dashboard latency — API consumers ordering by non-listed metrics bypass it. A porter "fixing" the lossiness reintroduces O(N×M) joins over millions of unique pathnames.
**Probe:** `grep -n '100' lib/plausible/stats/imported/imported.ex | grep -m1 '\* 100'` → :354 `n = (query.pagination.limit + query.pagination.offset) * 100`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^paginate_optimization$", fields: ["lines"], limit: 3 });
```

## Metric recombination needs hidden denominator columns
**Path/Symbol:** `lib/plausible/stats/imported/sql/expression.ex:joined_metric` (:359-459) + docstring (:353-357).
**Flow:** additive metrics sum directly (`s.visits + i.visits`); ratios recompute from parts: bounce_rate = `100*(i.bounces + s.bounce_rate*s.__internal_visits/100)/(s+i visits)`; views_per_visit and visit_duration likewise use `__internal_visits` as weights; time_on_page sums `__internal_total_time_on_page(_visits)`; scroll_depth defers to SpecialMetrics but pre-selects `__imported_total_scroll_depth(_visits)` here.
**Invariant:** Native query MUST emit the `__internal_visits` / `__internal_total_time_on_page` companion columns or the imported join crashes on missing keys — the naming convention is the cross-module contract (docstring even says reverse-computing bounces later is inefficient by design). Time dimension coalesce uses `greatest(s.time, i.time)`, string dims prefer native then imported.
**Probe:** `grep -c 'joined_metric' lib/plausible/stats/imported/sql/expression.ex` → 13; `grep -n '__internal_visits' lib/plausible/stats/imported/sql/expression.ex | head -1`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", file_pattern: "imported/sql/expression.ex", fields: ["lines"], limit: 20 });
```

## Verdict
Adopt routing-to-single-table, explicit skip-reason surfacing, and denominator-column recombination; adapt the ×100 constant to your latency budget; omit GA-specific import schemas.
