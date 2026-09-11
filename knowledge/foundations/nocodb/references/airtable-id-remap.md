<!-- capsule-v2 -->
# Airtable id remap — how do imported rows keep stable integer ids so links created later resolve deterministically?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What is the idMap/idCounter contract between data import and LTAR link import?

## deterministic per-table id assignment
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/at-import/helpers/readAndProcessData.ts:importData/importLTARData` id blocks (196-201, 251-256; 388-409).
**Signature:** `idMap: Map<atId, number>`; `idCounter: Record<tableId, number>` (next id per table); both SHARED across the whole import and threaded through every helper.
**Data Shape:** row insert body carries `id: idMap.get(_atId)` explicitly (`undo: true` allows system column); link tuples translate BOTH endpoints via the same map.

### Decisive source
```ts
// data phase:
const { _atId: rid, ...fields } = record;
if (!idMap.has(rid)) { idMap.set(rid, idCounter[table.id]++); }
tempData.push({ ...r, id: idMap.get(rid) });
...
// link phase (same maps):
if (!idMap.has(id)) {
  idMap.set(id, idCounter[assocMeta.colMeta.colOptions.fk_related_model_id]++);
}
assocTableData[assocMeta.modelMeta.id].push({
  [assocMeta.curCol.title]: idMap.get(_atId),
  [assocMeta.refCol.title]: idMap.get(id),
});
```

**Flow:** each Airtable record id gets a dense per-table integer on first sight; inserted rows carry that id explicitly. When a link references a not-yet-seen related record, it is ASSIGNED an id immediately and its real row materializes when its table's stream reaches it — forward references never dangle because both sides consult one map.
**Invariant:** ids are assigned ONCE per atId (guarded by `has` check) — re-assignment would split link endpoints. Counters are per-table, so id density holds even with interleaved table imports. Explicit ids require the bulk-insert path to permit system columns (`allowSystemColumn: true, undo: true`).
**Probe:** no unit test upstream; file parse_partial in graph — verified from source. Source-grounded probe: `readAndProcessData.ts:250-256` vs `:452-462` — identical has/set/get ladder in both phases.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "idMap idCounter importLTARData readAndProcessData", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt shared first-sight id assignment whenever links must be created before all referenced rows exist; adapt to your pk generation (skip if sequences suffice); omit explicit-id insertion if your DB forbids it (then two-phase with temp refs). Coverage caveat: graph parse_partial — source read directly.
