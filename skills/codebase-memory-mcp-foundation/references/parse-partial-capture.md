<!-- capsule-v2 -->
# Parse-partial coverage capture — how do you record exactly which source ranges failed to parse?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do tree-sitter ERROR regions become precise, aggregable line ranges that clear when fixed?

## error_ranges aggregation with arena-backed merge
**Path/Symbol:** `src/pipeline/pass_definitions.c:objectscript_export_append_strings` area (480–580 shows the aggregate pattern) + tests/test_parse_coverage.c (109–180) + `internal/cbm/helpers.c` region collection.
**Signature:** per-file result fields `parse_incomplete`, `error_ranges` ("start-end,start-end,…"), `error_region_count`; pipeline aggregates across files into coverage rows.
**Data Shape:** Clean file ⇒ no flag. Unrecovered garbage ⇒ range covering the failed region. Recovered constructs (e.g., a def salvaged after an #ifdef split-brace) do NOT count. Aggregation joins ranges comma-separated via arena sprintf.

### Decisive source
```c
TEST(c_ifdef_split_brace_sets_parse_incomplete) { ... }
TEST(c_ifdef_split_brace_neighbors_still_extracted) { ... }
TEST(c_error_range_points_at_failed_region) {
    ...
    ASSERT_EQ(sscanf(r->error_ranges, "%u-%u", &start, &end), 2);
}
TEST(py_recovered_def_not_flagged) { ... }
```

**Flow:** tree-sitter parse → collect ERROR/missing nodes into minimal enclosing line ranges → mark file parse_incomplete → neighbors still extracted → pass_definitions merges per-file strings → index_coverage rows carry kind=parse_partial + detail ranges → fixing the syntax clears rows on next index.
**Invariant:** Recovery-awareness is the hard part: a range must reflect what's MISSING, not where recovery happened; macro type-arg false positives (#1071) show why grammar-specific vetoes exist.
**Probe:** the four named tests plus `tests/test_pipeline.c:pipeline_env_access_configures_sequential_parallel_parity` for seq/par coverage equality; consumer contract in coverage-honesty capsule.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "error_ranges", limit: 5 });
```

## Verdict
Adopt range-precise parse telemetry over boolean flags; adapt aggregation format; pair with a clearing path so stale warnings die with their causes.
