<!-- capsule-v2 -->
# Incoming-link delete choreography — when a table's records are deleted, how do links stored in OTHER tables get cleaned and their sources seeded for recomputation?

## meta query for fields whose foreignTableId = target → seed sources BEFORE cleanup → junction-delete / fk-nullify by relationship, skipping own-table hosts except self-referential
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `loadIncomingLinkFields(metaDb, baseId, targetTableId)` (:5078–5146, meta query :5088–5101), `collectIncomingLinkExtraSeedRecords` (:5218–5298), `executeIncomingLinkCleanup` (:5153–5212); orchestration in `deleteMany` :3179–3206. Tests: `PostgresTableRecordRepository.delete.spec.ts` 'clears incoming junction links for normal link fields stored with is_lookup false' (:728).
**Signature:** `IncomingLinkFieldInfo {sourceTableId, fieldId, relationship, isOneWay, fkHostTableName, foreignKeyName, selfKeyName|null, orderColumnName|null}`.

### Decisive source
```sql
-- find every link field POINTING AT the dying table:
SELECT field.id, field.table_id, field.options
FROM field INNER JOIN table_meta ON table_meta.id = field.table_id
WHERE field.type = 'link' AND (field.is_lookup IS NULL OR field.is_lookup = false)
  AND table_meta.base_id = ${baseId}
  AND (field.options::json->>'foreignTableId')::text = ${targetTableId}
```
```ts
const isSelfReferential = sourceTableId === targetTableId;
if (fkHostTableName === targetTableName && !isSelfReferential) continue;   // FK dies with rows
// manyMany | oneMany+oneWay ⇒ DELETE FROM junction WHERE foreignKey IN (dying)
// manyOne  | oneOne         ⇒ UPDATE source SET foreignKey=NULL, orderColumn=NULL WHERE …
```

**Flow:** resolve incoming fields from META db → collect which SOURCE records currently point at the dying rows (per relationship shape: junction selfKey / source-table __id / symmetric two-way FK read from the dying rows themselves) into extraSeedMap → THEN execute cleanup so seeds are captured before the pointers vanish.
**Invariant:** ORDER IS THE CONTRACT: `collectIncomingLinkExtraSeedRecords` at :3190 precedes `executeIncomingLinkCleanup` at :3199 — after nullification/deletion the "who pointed here?" question is unanswerable, and without those seeds rollups on surviving source rows never recompute (silent staleness). The host-skip rule prevents touching the dying table itself EXCEPT for self-referential links where remaining siblings' FKs must still be nulled (:5174–5177). Lookup fields are excluded (`is_lookup` filter) because they are computed views, not storage.
**Probe:** delete.spec.ts :728/:996 pin incoming cleanup + before-image selection.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "loadIncomingLinkFields executeIncomingLinkCleanup collectIncomingLinkExtraSeedRecords", limit: 8 });
```
## Verdict
Adopt for referential cleanup in schema-per-table stores: discover inbound references from metadata, capture witness seeds first, then clean per relationship shape with an explicit self-reference carve-out.
