<!-- capsule-v2 -->
# Deferred virtual-column insert groups — why are relation creations queued per target table instead of inserted inline?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How does meta-sync create LTAR/Links columns for discovered FKs without two concurrent inserts computing the same unique title from a stale snapshot?

## syncBaseMeta virtualColumnInsertByTarget
**Path/Symbol:** `packages/nocodb/src/services/meta-diffs.service.ts:syncBaseMeta` (:877-1268); grouping map (:902-905), TABLE_RELATION_ADD case (:1106-1236), sequential drain (:1242-1255).
**Signature:** `const virtualColumnInsertByTarget = new Map<string, Array<() => Promise<void>>>()` — target table name → thunks; drained via `NcHelp.executeOperations(targetGroupRunners, source.type)`.
**Data Shape:** Each thunk closes over its change `{tn, rtn, cn, rcn, relationType, cstn, dr}`. Target selection: BELONGS_TO → child table (`change.tn`, an LTAR column on the FK-holding side); HAS_MANY → parent table (`change.rtn`, a Links column).

### Decisive source
```ts
// Group queued virtual-column inserts by target model so callbacks
// writing to the same model run sequentially. Without this, two
// concurrent inserts targeting the same table can each compute the
// same unique title against a stale snapshot.
```
```ts
// Run each per-target group sequentially so siblings inserting into the
// same model see each other's columns when computing unique titles.
// Different groups still run in parallel (via NcHelp.executeOperations).
const targetGroupRunners: Array<() => Promise<void>> = [];
for (const fns of virtualColumnInsertByTarget.values()) {
  targetGroupRunners.push(async () => { for (const fn of fns) await fn(); });
}
await NcHelp.executeOperations(targetGroupRunners, source.type);
```
and inside a thunk (HAS_MANY):
```ts
// Uniqueness is checked against parentModel.columns — the model the column is
// inserted into. Sibling HAS_MANY inserts for the same parent are serialized
// below so each sees the previous insert when computing its title.
const title = getUniqueColumnAliasName(parentModel.columns, pluralize(childModel.title || childModel.table_name));
await Column.insert<LinkToAnotherRecordColumn>(context, {
  // External-source relations use LinkToAnotherRecord (LTAR), not the
  // deprecated Links uidt. hm has no junction table, so the version heuristic
  // resolves this to LTAR v1.
  uidt: UITypes.LinkToAnotherRecord,
  ...
  description: formatLinkDbMapping({ kind: 'hm', ... }),
});
```

**Flow:** apply loop sorts detectedChanges by priority (VIEW_COLUMN_REMOVE + TABLE_RELATION_REMOVE first "to avoid foreign key constraint error") → most change types applied inline → RELATION_ADD enqueues a thunk per target table instead of inserting → after ALL tables processed, groups run: different tables parallel, same-table thunks strictly serial → finally extractAndGenerateManyToManyRelations sweeps junction tables into mm pairs.
**Invariant:** Title uniqueness (getUniqueColumnAliasName) reads the MODEL's in-memory column list — so serialization within a group is what makes sibling titles correct; per-group parallelism across DIFFERENT tables is safe because they never contend for one alias namespace. The FK column itself is first converted in place: `Column.update(childCol.id, {...childCol, uidt: UITypes.ForeignKey, system: true})`.
**Probe:** No runner at this pin — deterministic probes: search_graph resolves `MetaDiffsService.syncBaseMeta`; grep confirms exactly one `virtualColumnInsertByTarget` declaration and one `NcHelp.executeOperations(targetGroupRunners` call.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "virtualColumnInsertByTarget executeOperations", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt group-by-write-target deferral whenever generated names must observe sibling inserts: serialize within group, parallelize across groups. Adapt NcHelp.executeOperations (its dialect dispatch) to your runner pool. Omit the sort-to-priority step only if your diff vocabulary has no ordering-sensitive removals.
