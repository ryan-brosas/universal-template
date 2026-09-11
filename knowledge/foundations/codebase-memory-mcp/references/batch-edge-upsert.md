<!-- capsule-v2 -->
# Batch edge upsert — how do you insert 100k edges without per-row prepare overhead or dedup violations?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What does batch insertion guarantee about uniqueness and partial failure?

## Prepared batch with UNIQUE-coalescing semantics
**Path/Symbol:** `src/store/store.h:465` (`cbm_store_insert_edge_batch`) + engine in store.c; behavior pinned by tests/test_store_edges.c:313–331.
**Signature:** `int cbm_store_insert_edge_batch(cbm_store_t *s, const cbm_edge_t *edges, int count);`
**Data Shape:** Single prepared statement reused across the array inside one transaction; duplicate (source,target,type[,local_name]) keys coalesce via upsert instead of erroring; NULL array/zero count ⇒ OK no-op.

### Decisive source
```c
int rc = cbm_store_insert_edge_batch(s, edges, 9);      /* bulk path */
rc = cbm_store_insert_edge_batch(s, edges, 9);          /* re-insert is safe */
...
int rc = cbm_store_insert_edge_batch(s, NULL, 0);       /* validated no-op */
```

**Flow:** begin → prepare once → bind+step per row → commit → counts reflect UNIQUE-coalesced rows. Pairs with single-row `cbm_store_insert_edge` (which returns the rowid, existing OR new) so callers can dedup by identity.
**Invariant:** Batch and singleton paths must agree on uniqueness semantics — the #768 widened constraint (local_name_gen) applies to both.
**Probe:** `tests/test_store_edges.c:store_edge_dedup`, `store_imports_edge_local_name_coexist`, and the batch calls above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_insert_edge_batch", limit: 5 });
```

## Verdict
Adopt prepared-batch upserts over per-row prepare for any bulk loader; adapt constraint columns; keep the NULL-safe no-op contract for optional sections.
