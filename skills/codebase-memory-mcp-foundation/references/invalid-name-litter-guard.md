<!-- capsule-v2 -->
# Invalid-name litter guard — why does an empty project name create a `.corrupt` file in your CWD?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What was the #1425 failure chain, and what's the structural fix?

## Empty-name short-circuit BEFORE any store open
**Path/Symbol:** `src/mcp/mcp.c:resolve_store_internal` empty-name skip + tests/test_mcp.c:2922 (`tool_call_invalid_project_name_leaves_no_corrupt_litter_issue1425`).
**Signature:** resolve path derivation rejects empty/invalid names before `cbm_store_open_path_query`.
**Data Shape:** Failure chain (pre-fix): project:"" → SQLite treats "" as anonymous TEMP DB → integrity check fails on it → quarantine writes `.corrupt.<hex>` into the daemon CWD. Post-fix: "bad name"/"" ⇒ clean "not found" error; test chdirs to a scratch dir and counts `.corrupt.` litter == 0.

### Decisive source
```c
cbm_mcp_server_handle(srv, "... \"arguments\":{\"name_pattern\":\"x\",\"project\":\"bad name\"}}}");
bool clean_error = resp && strstr(resp, "not found") != NULL;
... if (strstr(entry->name, ".corrupt.")) { litter++; }
```

**Flow:** validate/derive path from project name → invalid ⇒ REQUIRE_STORE error path immediately, no open, no verdict, no quarantine.
**Invariant:** Never open a SQLite connection with a caller-derived empty filename — anonymous temp semantics turn a validation bug into filesystem pollution.
**Probe:** `tests/test_mcp.c:tool_call_invalid_project_name_leaves_no_corrupt_litter_issue1425`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "resolve_store", limit: 5 });
```

## Verdict
Adot validate-before-open for all derived filenames; adapt validators; keep the litter-counting test pattern — it catches side effects assertions miss.
