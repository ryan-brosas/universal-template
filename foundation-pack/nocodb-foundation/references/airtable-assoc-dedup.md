<!-- capsule-v2 -->
# Import LTAR assoc dedup — why does the link importer track inserted mm tables in insertedAssocRef, and how does it avoid double-importing shared junction rows?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does importLTARData ensure each many-to-many junction table is imported exactly once across all importing tables?

## insertedAssocRef + self-link skip
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/at-import/helpers/readAndProcessData.ts:importLTARData` (338-577).
**Signature:** `importLTARData(context, {insertedAssocRef = {}, ncLinkMappingTable, ...}): Promise<number>`; guard `if (colMeta.colOptions.fk_mm_model_id in insertedAssocRef) continue;`.
**Data Shape:** `assocTableMetas[]` = per-mm `{modelMeta, colMeta, curCol, refCol}` resolved once; `assocTableData[mmId]` buffers tuples to BULK_LINK_BATCH_COUNT (500) before insert.

### Decisive source
```ts
for (const colMeta of modelMeta.columns) {
  if (!isLinksOrLTAR(colMeta.uidt) ||
      colMeta.colOptions.type !== RelationTypes.MANY_TO_MANY) continue;
  // skip if already inserted
  if (colMeta.colOptions.fk_mm_model_id in insertedAssocRef) continue;
  // self links: skip if the column under consideration is the add-on column
  if (ncLinkMappingTable.every((a) => a.nc.title !== colMeta.title)) continue;
  // mark as inserted
  insertedAssocRef[colMeta.colOptions.fk_mm_model_id] = true;
  ...
}
...
// links can be [] & hence assocTableData[...] can be [].
if (assocTableData[id]?.length >= BULK_LINK_BATCH_COUNT) { flush via bulkDataInsert }
```

**Flow:** two tables sharing one mm junction (A↔B seen from both sides) would each try to import its pairs; the first column that reaches its mm table claims it in insertedAssocRef and the mirror column skips. Self-referential add-on columns are filtered by checking the link mapping table so NocoDB-generated mirror columns don't re-trigger. Tuples buffer to 500 then bulk-insert with FK checks relaxed for meta sources.
**Invariant:** claim-before-work (`insertedAssocRef[fk_mm_model_id] = true` BEFORE resolving assoc meta) — not after success — because a crash mid-junction is safer retried wholesale than partially claimed twice. The final flush runs even when length is 0 (`>= 0`) so empty junctions still complete deterministically.
**Probe:** no unit test upstream; parse_partial file — verified from source. Source-grounded probe: `readAndProcessData.ts:388-409` — the three-continue guard ladder ending in the mark; `:505-513` — `>= BULK_LINK_BATCH_COUNT` flush.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "insertedAssocRef fk_mm_model_id importLTARData assoc", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt junction-table claiming for any multi-source link backfill; adapt batch count and FK-check policy; omit Airtable self-link specifics once your schema has no mirror columns. Coverage caveat: graph parse_partial — source read directly.
