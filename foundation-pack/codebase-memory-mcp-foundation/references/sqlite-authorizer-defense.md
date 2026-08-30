<!-- capsule-v2 -->
# SQLite authorizer defense — how do you neutralize SQL-injection file access when a query language compiles to SQL?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** If your Cypher-to-SQL translator had a bug, what backstop stops `ATTACH DATABASE '/tmp/evil.db'` from creating files?

## set_authorizer deny for ATTACH/DETACH
**Path/Symbol:** `src/store/store.c:store_authorizer` (663–680), installed in both `store_open_internal` (712) and the query-only open (903).
**Signature:** `static int store_authorizer(void*, int action, ...);` returning SQLITE_DENY for `SQLITE_ATTACH`/`SQLITE_DETACH`, else SQLITE_OK.
**Data Shape:** Installed on EVERY connection (read-write and read-only); runs inside SQLite's core — no string-level bypass exists.

### Decisive source
```c
/* Security: block ATTACH/DETACH to prevent file creation via SQL injection.
 * The authorizer runs inside SQLite's query planner — no string-level bypass. */
case SQLITE_ATTACH: /* could create/read arbitrary files */
case SQLITE_DETACH:
    return SQLITE_DENY;
```

**Flow:** open → install authorizer before any user-influenced statement → Cypher parser independently rejects non-Cypher syntax, so an ATTACH never even parses; if a future translator bug emitted one, the authorizer denies at prepare/plan time → tests assert both layers.
**Invariant:** Defense IN DEPTH: parser rejection and authorizer denial must BOTH hold; installing on only some open paths is a hole.
**Probe:** `tests/test_security.c:sqlite_blocks_attach_via_cypher`, `sqlite_blocks_attach_direct`, `sqlite_blocks_detach_direct`, `sqlite_allows_normal_queries`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "store_authorizer", limit: 5 });
```

## Verdict
Adopt authorizer-level denies for any capability you cannot express via grants (file IO, attach); adapt the action list to your threat model; keep the parse-layer check too — the test pins both.
