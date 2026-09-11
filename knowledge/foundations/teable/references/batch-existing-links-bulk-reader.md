<!-- capsule-v2 -->
# Batch existing-link reader — how do you prefetch current link state for N records in ONE query per relationship shape without N+1 reads?

**Source:** teable AGPL-3.0 `develop@06a4461e2bc5`; Codebase Memory `teable`. **Question:** What is the bulk counterpart of the per-record `loadExistingLinkRecordIds`, and what are its pre-seeding and external-host rules?

## IN-query batch reader
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/PostgresTableRecordRepository.ts:loadExistingLinkRecordIdsBatch` (:4387–4503); consumed at :3153 (batch updateManyStream link-change collection).
**Signature:** `async (db, tableName, recordIds: ReadonlyArray<string>, field: core.LinkField, logger): Promise<Result<Map<string, string[]>, DomainError>>`.
**Data Shape:** returns Map with EVERY input recordId pre-seeded to `[]` (:4397–4400) before any query — callers can index without existence checks. One SELECT ... WHERE key IN (...) per call; rows grouped client-side into the map.

### Decisive source
```ts
const result = new Map<string, string[]>();
for (const recordId of recordIds) result.set(recordId, []);   // pre-seed BEFORE queries
...
if (!hostCheckResult.value) return ok(result);                // external/missing host → EMPTY, not error
// junction shape:  SELECT selfKey AS self_key, foreignKey AS foreign_key
//                  FROM junction WHERE selfKey IN (...)         → append per row
// manyOne/oneOne:  SELECT __id, fk FROM tableName WHERE __id IN (...) → result[id] = [fk]
// oneMany two-way: SELECT selfKey, __id FROM foreignTable WHERE selfKey IN (...) → append per row
```
`preflightExternalLinkHostTable(db, field, logger, 'load-existing', recordIds.length)` gates ALL shapes; on missing/unreadable host table it returns the all-empty map (fail-open parity with the single-record path's tolerance).
**Flow:** pre-seed → host preflight → relationship dispatch → one IN-query → group rows into map.
**Invariant:** Pre-seeding is load-bearing: downstream diff logic assumes every requested record has an entry, so "record had no links" and "record wasn't read" must be indistinguishable HERE. Non-string cell values are skipped silently (defensive against BYODB column type drift). Unlike the single reader, the batch variant does NOT apply order columns — consumers needing ordered diffs use the per-record reader or re-sort.
**Probe:** no dedicated unit spec; exercised through `updateMany.pglite.spec.ts` flows that assert link-change outcomes — caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "loadExistingLinkRecordIdsBatch preflightExternalLinkHostTable", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pre-seeded-map + one-IN-query-per-shape + fail-open host preflight as the bulk-read contract. Adapt to your SQL toolkit; keep the "every requested key present" invariant even when adding order support. Omit teable's external-host (BYODB) preflight internals if your storage is single-postgres. Coverage caveat: integration-level evidence only.
