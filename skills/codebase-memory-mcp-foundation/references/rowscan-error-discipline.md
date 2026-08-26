<!-- capsule-v2 -->
# Row-scan error discipline — why does discarding the terminal sqlite3_step code silently corrupt every query result?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What invariant must every row-fetch loop satisfy so a mid-stream CORRUPT cannot masquerade as end-of-rows?

## SCANCHK pattern: step rc must equal SQLITE_DONE
**Path/Symbol:** `src/store/store.c` — exemplars at `cbm_store_search` (4510–4529) and the #896 regression test tests/test_store_pragmas.c:150+.
**Signature:** `while ((scan_rc = sqlite3_step(stmt)) == SQLITE_ROW) { ... } if (scan_rc != SQLITE_DONE) { store_set_error_sqlite(s, "row scan aborted"); ... return CBM_STORE_ERR; }`
**Data Shape:** Counts answered from covering indexes may stay CORRECT while row fetches die at the first corrupt page — the old loops discarded the terminal code, so every surface returned plausible truncated results.

### Decisive source
```c
if (scan_rc13 != SQLITE_DONE) { /* SCANCHK:13:main_stmt */
    store_set_error_sqlite(s, "row scan aborted");
    sqlite3_finalize(main_stmt);
    like_pool_free(&like_pool);
    out->results = results;
    out->count = n;
    return CBM_STORE_ERR;
}
```
```c
/* #896: a row-scan that dies mid-stream (SQLITE_CORRUPT) must surface a loud
 * store error, not masquerade as a clean end of results. */
```

**Flow:** loop steps rows into the output buffer while capturing each step's return → after the loop, REQUIRE DONE before reporting success → on any other terminal code, finalize, free per-loop resources, still hand back partial results with count but flag ERR so callers can distinguish.
**Invariant:** Every `while(step()==ROW)` needs the trailing DONE check; partial output is allowed only when paired with an error return.
**Probe:** `tests/test_store_pragmas.c:corrupt_page_scan_returns_error_not_truncation` and the in-loop SCANCHK markers across cbm_store_search / qn_suffix / find_nodes_by_file.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "row scan aborted", limit: 5 });
```

## Verdict
Adopt SCANCHK as a lint-level rule for all SQLite consumers; adapt the error channel; nothing to omit — this is pure discipline.
