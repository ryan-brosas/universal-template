<!-- capsule-v2 -->
# Cross-repo mutation guard — how do you acquire N project locks in a safe order and always unwind?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What are the sort/dedupe/cancel rules for multi-project mutation, and what target syntax is rejected?

## Sorted-deduped lease acquisition + wildcard exclusivity + cancel checks
**Path/Symbol:** `src/mcp/mcp.c` cross_repo mutation guard + tests/test_mcp.c:5821 (`tool_cross_repo_mutation_guard_sorts_dedupes_and_unwinds`), 5891 (casefolds aliases), 5956 (`rejects_wildcard_mixed_with_named_targets`), 6008 (`checks_cancellation_after_acquiring_leases`), 6068 (`missing_inputs_fail_without_creating_ghost_databases`).
**Signature:** index_repository mode=cross-repo-intelligence with target_projects:[...]; guard probes injected via cbm_mcp_server_set_project_mutation_guard.
**Data Shape:** Targets: named list or lone `"*"` — mixing `*` with named ⇒ isError explaining "only/combine". Leases acquired in sorted (casefolded-alias) order; cancellation checked AFTER each acquisition; any failure unwinds ALL held leases.

### Decisive source
```c
"{\"repo_path\":\"%s\",\"mode\":\"cross-repo-intelligence\","
"\"target_projects\":[\"*\",\"named-target\"]}"
bool rejected = resp && strstr(resp, "\"isError\":true") != NULL;
```

**Flow:** validate inputs BEFORE creating anything (missing inputs must not leave ghost DBs) → normalize/sort targets → acquire leases sequentially with cancel checkpoints → run → unwind in reverse.
**Invariant:** Sorted acquisition prevents deadlock cycles; post-acquisition cancel checks make Ctrl-C responsive mid-fan-out; input validation precedes side effects.
**Probe:** the five named tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "mutation_guard", limit: 5 });
```

## Verdict
Adopt ordered multi-resource acquisition with cancel checkpoints for fan-out mutations; adapt alias normalization; never create artifacts before validation completes.
