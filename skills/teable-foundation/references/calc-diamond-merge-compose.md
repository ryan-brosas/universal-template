<!-- capsule-v2 -->
# Duplicate-change merge + op-map composition — what makes calculated OT ops idempotent under diamond dependencies?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How do multi-path recomputations collapse into one op per cell path without double-applying?

## mergeDuplicateChange / composeOpMaps
**Path/Symbol:** `apps/nestjs-backend/src/features/calculation/utils/changes.ts:mergeDuplicateChange` (:41–60); `apps/nestjs-backend/src/features/calculation/utils/compose-maps.ts:composeOpMaps` (:9–47).
**Signature:** `mergeDuplicateChange(changes: ICellChange[]): ICellChange[]`; `composeOpMaps(opsMaps: (IOpsMap|undefined)[]): IOpsMap`.
**Data Shape:** `ICellChange = {tableId, recordId, fieldId, oldValue, newValue}`; ops keyed by JSON path `op.p.join()`.

### Decisive source
```ts
/**
 * when update multi field in a record, there may be duplicate change.
 * see this case, A and B update at the same time
 * A -> C -> E
 * A -> D -> E
 * B -> D -> E
 * D will be calculated twice
 * E will be calculated twice
 * so we need to merge duplicate change to reduce update times
 */
for (const change of changes) {
  const key = `${change.tableId}#${change.fieldId}#${change.recordId}`;
  if (indexCache[key] !== undefined) {
    mergedChanges[indexCache[key]].newValue = change.newValue;   // LAST value wins, first slot kept
  } else { ... push ... }
}
```
```ts
// compose op that has same path
composedMap[tableId][recordId][existingOpIndex] = { p: op.p, od: oldOp.od, oi: op.oi };
...
// filter op that has same oi and od
composedMap[tableId][recordId] = composedMap[tableId][recordId].filter((op) => !isEqual(op.oi, op.od));
```

**Flow:** Merge collapses repeated (table#field#record) changes keeping the FIRST position but the LAST newValue — order-preserving for consumers while semantically final. Composition then merges per-record op arrays across calculation rounds: same-path ops compose as `{p, od: ORIGINAL od, oi: NEWEST oi}` (the chain's true before/after), and any op whose od equals its oi is DELETED outright (no-op round-trips vanish), pruning empty records/tables bottom-up.
**Invariant:** The composed op must carry the FIRST od with the LAST oi — naively concatenating ops would replay intermediate values against already-updated DB rows. Diamond fan-in (E reachable via C and D) is the normal case in dependency graphs, not an anomaly.
**Probe:** direct tests `utils/changes.spec.ts` :67 ('should merge duplicate changes') and `utils/compose-maps.spec.ts` ('should overwrite operations with the same "p" value…' ×3, 'should filter operations with the same oi od…' ×2).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "mergeDuplicateChange composeOpMaps IOpsMap", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt first-slot/last-value merge + od-preserved path composition + no-op elimination as one indivisible trio; adapt to your change format; omit table-nesting if flat.
