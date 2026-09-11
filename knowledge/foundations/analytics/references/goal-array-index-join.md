<!-- capsule-v2 -->
# Goal join as array-intersection index — matching events to N goals in one scan instead of N joins

**Source:** Plausible Analytics AGPL-3.0 `master@9cc669b9`; Codebase Memory `ext-analytics`. **Question:** How does `GROUP BY event:goal` work against a table with no goal column, and why is there a separate no-props fragment?

## Compile-time macro over parallel goal arrays
**Path/Symbol:** `lib/plausible/stats/sql/expression.ex:event_goal_join` macro (:515-548) + `event_goal_join_no_props` (:556-582); arrays built by `lib/plausible/stats/goals.ex:goal_join_data` (:81-118).
**Signature:** macro receives `%{indices, event_names_by_type, page_regexes, scroll_thresholds, custom_props_keys, custom_props_values}`; emitted SQL returns `[UInt32]` of 1-based goal indices per event.
**Data Shape:** Five parallel arrays (one slot per preloaded goal): expected event name, scroll threshold, original index, per-goal props keys/values. Event goals get regex `".?"` (match-everything placeholder at goals.ex :129).

### Decisive source
```sql
arrayIntersect(
  multiMatchAllIndices(?, e.pathname),          -- which page regexes hit?
  arrayMap(
    (expected_name, threshold, index, custom_props_keys, custom_props_values) -> if(
      expected_name = e.name and ? between threshold and 100 and
      (empty(custom_props_keys) OR arrayAll((k, v) -> meta.value[indexOf(meta.key, k)] = v, ...)),
      index, -1),
    ...arrays...))
```

**Flow:** `multiMatchAllIndices` finds candidate goals by page pattern → `arrayMap` keeps indices whose name/threshold/props also match → intersect yields all matching goal indices → that ARRAY becomes the GROUP BY key → QueryRunner decodes index→goal (`Enum.at(goals, idx-1)`).
**Invariant:** (1) Index positions must stay aligned across ALL five arrays — they're zip-encoded, not keyed; (2) the no-props variant exists ONLY to avoid reading the expensive `Array(String) meta.key/meta.value` columns when no goal has props (docstring :550-555) — a porter who unconditionally uses the full fragment pays a big scan penalty; (3) `between threshold and 100` bounds scroll goals above by 100.
**Probe:** `test/plausible/stats/query/query_parse_and_build_test.exs:1865` ("succeeds with event:goal dimension") pins parse+preload path; `grep -c 'multiMatchAllIndices' lib/plausible/stats/sql/expression.ex` → 2.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^event_goal_join$", fields: ["lines"], limit: 4 });
```

## Goal FILTERS are OR-ed per-clause conditions, not the join
**Path/Symbol:** `lib/plausible/stats/goals.ex:add_filter` (:52-71), `goal_condition/3` (:197-241).
**Flow:** filtering `[:is, "event:goal", ["A","B"]]` reduces over clauses building `dynamic(condition or acc)` from the PRELOADED goal list filtered by clause; each condition compiles name/page/scroll/props predicates directly against event columns.
**Invariant:** Filter semantics differ from group-by semantics: filters validate against site-configured goals (unknown goal ⇒ API error raised upstream in query parsing), while grouping enumerates every matching goal via the index mechanism. Porting one to serve the other breaks either error handling or multi-goal rows.
**Probe:** `test/plausible/stats/query/query_builder_test.exs:117` ("event goal name is checked within behavioral filters") pins unknown-goal rejection inside `[:has_done, ...]`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", qn_pattern: "stats.goals$", fields: ["lines"], limit: 12 });
```

## Verdict
Adopt the parallel-array single-scan join for any "dimension computed by predicate set" problem; adapt prop-matching to your map encoding; omit EE revenue-currency plumbing around goals.
