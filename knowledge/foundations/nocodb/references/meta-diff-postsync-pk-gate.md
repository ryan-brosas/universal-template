<!-- capsule-v2 -->
# Post-sync PK prediction — why must LTAR-removal detection look at the schema you are ABOUT to write, not the metadata you have?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How do you flag a relation for removal because a table "has no primary key" without undoing the pk recovery that this same sync is performing?

## getMetaDiff PK-prediction gate + TABLE_RELATION_ADD skip
**Path/Symbol:** `packages/nocodb/src/services/meta-diffs.service.ts:hasPostSyncPk` (:451-457) inside the virtualRelationColumns loop; creation-side twin at :1145-1157 (TABLE_RELATION_ADD case).
**Signature:** `const hasPostSyncPk = (model: Model): boolean => { if (model.primaryKey) return true; const dbCols = colListRef[model.table_name]; return !!(dbCols && dbCols.find((c: any) => c.pk)); }`.
**Data Shape:** `colListRef` = table_name → DB column list introspected EARLIER in this same run. A stored model with `primaryKey == null` may still gain one because an earlier TABLE_COLUMN_PROPS_CHANGED apply in THIS pass will write `pk:true` from what sqlClient reports.

### Decisive source
```ts
// If either side of the relation no longer has a primary key, the
// LTAR is unusable — every read path that builds nested record JSON
// dereferences `relatedModel.primaryKey.column_name` and crashes.
// Mark it for removal so meta-sync naturally cleans up legacy bad
// state (LTARs created before the prevention guard in
// TABLE_RELATION_ADD shipped). The matching TABLE_RELATION_ADD path
// skips creation while PKs are still missing, so this won't oscillate
// — once the user re-flags `pk` (or the source schema gains a PK),
// the next sync recreates the LTAR.
//
// Predict the post-sync pk state instead of reading only the stale
// NocoDB metadata. A column-prop-changed apply earlier in this same
// sync may set `pk:true` from what the sqlClient reports — without
// this prediction, the LTAR-removal flag would be raised in the same
// pass that's about to restore the pk, and the removal would still
// apply later, undoing the recovery.
```
and the creation-side mirror:
```ts
// Skip relation creation if either side has no primary key.
// PK-less tables (e.g. PG junction tables without a PK constraint) can't be
// addressed by row id, so cascading deletes, link broadcasts, and undo all
// break downstream (see delByPk, updateLinkedRecordsOnDelete). Leave them as
// plain tables so the FK column is still imported, just without the LTAR
// virtual column.
if (!parentModel.primaryKey || !childModel.primaryKey) { logger?.(...); return; }
```

**Flow:** per virtual relation: resolve parent/child columns+models → missing column/model ⇒ TABLE_RELATION_REMOVE → compute parentHasPk/childHasPk via hasPostSyncPk (stored pk OR db-introspected pk from colListRef) → either side false ⇒ TABLE_RELATION_REMOVE ('parent|child table has no primary key') → mm-like relations additionally verify junction model/table/columns exist else TABLE_VIRTUAL_M2M_REMOVE → non-virtual bt/hm verify the FK still exists in relationList (found-marking) else REMOVE; ON-DELETE drift compares normalizeDr(db.dr) vs normalizeDr(meta.dr) ⇒ TABLE_RELATION_CHANGED.
**Invariant:** Detection and creation must use SYMMETRIC pk gates (removal predicts post-sync state; creation refuses when pks absent) or the pair oscillates across syncs: remove fires while add would immediately recreate. The prediction reads colListRef populated by the SAME run — ordering within getMetaDiff/syncBaseMeta is load-bearing.
**Probe:** No runner at this pin — deterministic probes: search_graph resolves `MetaDiffsService.getMetaDiff` :163-839 (gate lives inside); grep confirms exactly one `hasPostSyncPk` definition (:451) and the creation-side skip string 'because one of the tables has no primary key' (:1154).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "hasPostSyncPk primary key relation remove", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt symmetric detect/create gates around any derived object whose validity depends on a property another step of the same pipeline may restore. Adapt the crash rationale (nested JSON dereference) to your read paths. Omit the mm witness ladder if you lack junction-table links.
