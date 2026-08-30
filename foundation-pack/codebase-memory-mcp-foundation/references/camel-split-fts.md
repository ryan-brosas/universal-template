<!-- capsule-v2 -->
# Camel-split FTS tokenizer — how do you make BM25 match `updateCloudClient` when the user types "update client"?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What SQLite function shape indexes both the original identifier and its word-split twin?

## Emit "original + space-split copy" as one FTS cell
**Path/Symbol:** `src/store/store.c:sqlite_camel_split` (539–573) + `camel_should_split` (521–537) + FTS rebuild usage (`generation_rebuild_fts`, pipeline.c 1496–1510).
**Signature:** `static void sqlite_camel_split(sqlite3_context *ctx, int argc, sqlite3_value **argv);` — registered `SKIP_ONE` arg, DETERMINISTIC.
**Data Shape:** Output = original token, then a space, then the split form; whitespace tokenizer therefore indexes BOTH. Split rules: lowercase→uppercase boundary AND uppercase-run→uppercase-followed-by-lowercase ("XMLParser" → "XML Parser", not "X M L Parser"); snake_case already splits on `_` via unicode61.

### Decisive source
```c
/* Emits the original identifier plus a space-separated split version, so FTS5's
 * whitespace tokenizer produces both `updateCloudClient` (exact match) and the
 * word tokens `update`, `cloud`, `client`. */
...
int len = snprintf(buf, sizeof(buf), "%s ", input);
if (len < 0 || len >= (int)sizeof(buf)) {
    /* Input too long — fall back to the original string unmodified. */
```

**Flow:** FTS index build calls `cbm_camel_split(name)` per row → both spellings land in the same column → BM25 queries in either style hit → full-rebuild path deletes-all and re-inserts with the split function (falling back to raw names if the UDF errors).
**Invariant:** The leading original string must be preserved verbatim FIRST (exact-match queries depend on it); overflow falls back to unmodified input rather than truncating mid-token.
**Probe:** exercised by every search via nodes_fts (e.g., tests/test_pipeline.c:2491 asserts the rebuilt FTS uses `cbm_camel_split(name)`), and semantic tokenize twins `tests/test_semantic.c:sem_tokenize_camel`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "sqlite_camel_split", limit: 5 });
```

## Verdict
Adopt dual-form emission for FTS over identifiers; adapt split rules to your naming conventions; omit the rebuild fallback branch if your schema always creates FTS with the UDF present.
