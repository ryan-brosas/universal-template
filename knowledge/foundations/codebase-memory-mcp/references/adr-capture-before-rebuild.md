<!-- capsule-v2 -->
# ADR capture-before-rebuild — how does an index rebuild preserve user-authored decisions stored in the OLD database?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** Where in the pipeline must the old ADR be read, and which failures must abort vs degrade?

## Read-only capture with ABORT_PRESERVE_DB on failure
**Path/Symbol:** `src/pipeline/pipeline.c:capture_existing_adr` (1316–1350) + store-side `cbm_store_adr_get` legacy-table probe (store.c 8106–8128).
**Signature:** `static int capture_existing_adr(cbm_pipeline_t *p, const char *db_path);`
**Data Shape:** Opens the existing DB via `cbm_store_open_path_query` (read-only); NOT_FOUND ⇒ no ADR, clear saved copy and continue; any OTHER failure (open fail, read error, strdup OOM) ⇒ `CBM_PIPELINE_ABORT_PRESERVE_DB` — never proceed to a rebuild that would orphan user content. Test-only fault hook can force the abort.

### Decisive source
```c
cbm_store_t *adr_store = cbm_store_open_path_query(db_path);
if (!adr_store) return CBM_PIPELINE_ABORT_PRESERVE_DB;
cbm_adr_t existing = {0};
int adr_rc = cbm_store_adr_get(adr_store, p->project_name, &existing);
if (adr_rc == CBM_STORE_NOT_FOUND) { /* genuinely no ADR */ ... return 0; }
if (adr_rc != CBM_STORE_OK || !existing.content) { ... return CBM_PIPELINE_ABORT_PRESERVE_DB; }
```

**Flow:** before routing/rebuild → capture → stash content on the pipeline (`p->saved_adr`) → publication writes it into the staging DB (`generation->adr_content`) so graph and ADR publish atomically together.
**Invariant:** Distinguish "no ADR" (progress) from "could not read ADR" (abort); capture must precede ANY destructive step of the rebuild.
**Probe:** serialization pinned end-to-end by `tests/test_daemon_application.c:daemon_application_serializes_adr_mutation_with_index_job`; fault path behind CBM_INCREMENTAL_TEST_API at tests/test_pipeline.c:1300s.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "capture_existing_adr", limit: 5 });
```

## Verdict
Adopt capture-with-abort semantics for user data living beside derived artifacts; adapt the storage key; keep NOT_FOUND-vs-error separation — conflating them is how user content gets destroyed.
