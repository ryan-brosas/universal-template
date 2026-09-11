<!-- capsule-v2 -->
# Case-insensitive search — how do you match identifiers regardless of case without breaking exactness?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** Where does case folding happen in the search stack?

## LIKE default-insensitive + iregexp for patterns
**Path/Symbol:** tests/test_store_search.c:811 (`store_search_case_insensitive`); LIKE/iregexp split in store.c search arms.
**Signature:** params->case_sensitive flag on cbm_store_search.
**Data Shape:** Default (insensitive): name matching via SQLite LIKE (ASCII-fold) and regex via `iregexp(pattern, col)`; explicit case_sensitive=true switches to REGEXP. Exact-match arms (`qualified_name = ?`) stay byte-exact ALWAYS.

### Decisive source
```c
TEST(store_search_case_insensitive) { ... }
```

**Flow:** build pattern arm → choose LIKE/iregexp vs REGEXP by flag → keep equality arms untouched so QN lookups never fold.
**Invariant:** Folding must NEVER apply to identity comparisons (upsert dedup, qn suffix exact arm) or you create duplicate nodes differing only by case.
**Probe:** the named test; identity-side guarantees in store_nodes tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_search", limit: 5 });
```

## Verdict
Adopt flag-gated folding with hard exact-identity exceptions; adapt collation if you need Unicode folds; document which fields fold.
