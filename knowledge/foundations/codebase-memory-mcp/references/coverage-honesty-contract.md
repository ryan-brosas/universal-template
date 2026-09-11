<!-- capsule-v2 -->
# Coverage honesty contract — how do you report "what the index might have missed" so agents never over-trust it?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do skipped/parse_partial/not_indexed classes and generation stamps combine into a checkable coverage verdict?

## Three issue classes + generation_matches gate
**Path/Symbol:** `src/pipeline/pipeline_internal.h` (coverage rows) + `cbm_store_coverage_replace_ex` (store.c 2918–3050) + tool layer tests tests/test_mcp.c:2577–2850; resilience suite tests/test_index_resilience.c.
**Signature:** `int cbm_store_coverage_replace_ex(cbm_store_t *s, const char *project, const cbm_coverage_row_t *rows, int count, const cbm_coverage_meta_t *meta);`
**Data Shape:** Row kinds: `skipped` (not indexed at all: oversized/read/parse failure), `parse_partial` (indexed but constructs inside listed line ranges MAY be missing), vs BY-DESIGN `not_indexed` (gitignore/.cbmignore/skip lists — not failures). Meta: {generation (=project indexed_at), coverage_version=3, hash_records_complete, index_mode}.

### Decisive source
```c
/* COVERAGE: ... 'skipped' ... and 'parse_partial' ... The embedded lists carry
 * counts plus a FEW EXAMPLES only; the complete lists are in the per-run
 * 'logfile' ... Both signals are best-effort: absence of a flag is NOT a
 * completeness guarantee; prefer grep inside flagged ranges. */
...
if (rc != CBM_STORE_OK) { store_set_error_sqlite(...); (void)exec_sql(s,"ROLLBACK;"); }
```

**Flow:** pipeline records per-file issues during discovery/extraction → publish writes rows+meta in ONE transaction (delete-all, batch insert, NOT-IN prune, meta upsert) → check_index_coverage re-reads requested paths, compares stored generation against CURRENT project indexed_at (`generation_matches`) and file metadata freshness → stale ⇒ status coverage_unavailable with recommended_action read_source_and_reindex instead of stale data.
**Invariant:** Embedded example lists are truncated by design (status caps) while the full catalog stays queryable; every response carries the best-effort caveat verbatim.
**Probe:** `tests/test_mcp.c:tool_check_index_coverage_finds_path_beyond_status_cap`, `tool_check_index_coverage_rejects_stale_generation`, `tool_check_index_coverage_reports_paths_scopes_and_ranges`; producers in `tests/test_index_resilience.c:index_oversized_file_reported`, `index_parse_partial_clears_on_fix`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "check_index_coverage", limit: 5 });
```

## Verdict
Adopt explicit issue-class taxonomy + generation-gated freshness for any indexer; adapt row schema; omit the logfile indirection if you can always embed full lists.
