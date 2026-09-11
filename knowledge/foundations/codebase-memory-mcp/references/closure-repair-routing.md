<!-- capsule-v2 -->
# Closure-repair incremental routing — when is a partial re-index safe, and what must always fall back to full?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** Given per-file content hashes and persisted LSP surfaces, which files must re-parse after an edit — and when must the planner refuse?

## Decline-first closure planner
**Path/Symbol:** `src/pipeline/pipeline_incremental.c:cbm_pipeline_run_incremental` (2354–2451) + `closure_try_plan` (1640–1902).
**Signature:** `static int closure_try_plan(p, store, project, files, file_count, stored, stored_count, fresh, fresh_count, closure_plan_t *plan);`
**Data Shape:** Routing is BINARY: exact semantic-manifest match (coverage_version + hash_records_complete + same index_mode + identical sorted sha manifest) ⇒ NOOP; any virtual/config/new-file delta or planner decline ⇒ FORCE_FULL_REINDEX; only body/signature edits with bounded dependents get CLOSURE_REPAIR. Budget: closure > 8 files AND > 30% of the repo declines.

### Decisive source
```c
if (synthetic)          { decline = "semantic_input_changed"; goto done; }
if (discovered) {
    if (!old_row)       { decline = "new_file";               goto done; }
    changed_paths[n_changed++] = (char *)fresh[i].rel_path; continue;
}
... if (!stored_row || !fresh_row) { decline = "missing_surface_row"; goto done; }
if (strcmp(stored_row->surface_sha, fresh_row->surface_sha) == 0)
    continue; /* body edit: the file re-resolves, nobody else does */
if (... surface_added_names(...) || added) { decline = "added_definition_names"; goto done; }
```

**Flow:** read-only open of the sealed generation → compare manifests → NOOP on exact match → else probe fresh LSP surfaces for changed files → early-cutoff: unchanged `surface_sha` means only the file itself re-resolves → a CHANGED surface (without ADDED names) seeds a dependent query (`get_dependent_files`) → closure = changed ∪ dependents ∪ config-governed seeds → budget check → executor purges deleted files' nodes and re-parses the closure.
**Invariant:** Every uncertain case DECLINES inside the planner making full rebuild the unconditional fallback; missing surface rows fail closed; dependents outside current discovery decline.
**Probe:** `tests/test_pipeline.c:pipeline_closure_repair_body_edit_converges_with_fresh_full`, `pipeline_closure_repair_added_name_declines_to_full`, `pipeline_closure_repair_budget_declines_to_full`; surface invariance pinned by `pipeline_lsp_surface_persisted_and_body_edit_invariant`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "closure_try_plan", limit: 5 });
```

## Verdict
Adopt the decline-first planner posture, surface_sha early cutoff, and the budget valve; adapt the dependent-file query to your edge schema; omit the legacy mtime+size classify path (kept only behind a test API).
