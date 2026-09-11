<!-- capsule-v2 -->
# Layered evaluation ordering — why must lookup columns be materialized before formulas that read them?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** In what order are impacted computed fields evaluated within one pass?

## buildFieldLayers / topoSortFieldLevels
**Path/Symbol:** `apps/nestjs-backend/src/features/record/computed/services/computed-evaluator.service.ts:ComputedEvaluatorService.buildFieldLayers` (:148–202), `topoSortFieldLevels` (:220–273).
**Signature:** `buildFieldLayers(entries): Promise<Array<Map<tableId, Set<fieldId>>>>`; `topoSortFieldLevels(fieldIds, edges): Map<fieldId, level> | null`.

### Decisive source
```ts
const levels = this.topoSortFieldLevels(uniqueFieldIds, edges);
if (!levels) {
  return this.buildDefaultLayers(entries);        // cycle → ONE flat layer, never fail   // :170–172
}
...
return result.length === fieldIds.length ? levels : null;                              // :272
// deterministic tie-breaks
queue.sort((a, b) => (orderIndex.get(a) ?? 0) - (orderIndex.get(b) ?? 0));            // :267
// stored-lookup gating is INVERTED
private shouldPreferStoredLookupFields(fieldInstances: IFieldInstance[]): boolean {
  ...
  return !fieldInstances.some((field) => ...isLookup === true ||
    field.type === FieldType.Rollup || field.type === FieldType.ConditionalRollup);    // :292–297
```

**Flow:** dependency edges load ONLY between impacted fields (`from IN (...) AND to IN (...)`, Prisma.sql :204–218); Kahn levels assign each field to evaluation wave = longest path from roots; per layer+table a fresh query builder projects that layer's fields; `preferStoredLookupFields` is TRUE only when NO rollup-ish field is present (later layers reading persisted lookups use STORED columns). The direct spec pins exactly this pair.
**Invariant:** Cycle or partial-topology ⇒ single flat layer fallback (correctness via recomputation order-independence, availability over strictness); NEVER throw on cyclic references — errored fields carry their own handling downstream. Level of a node = max over predecessors +1, not insertion count.
**Probe:** `apps/nestjs-backend/src/features/record/computed/services/computed-evaluator.service.spec.ts` ("uses stored lookup columns only after lookup-like fields have been evaluated", :86–137 asserts call[0].preferStoredLookupFields===false then true).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "topoSortFieldLevels", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt layered topo evaluation + flat-layer cycle fallback; adapt the inverted stored-column gate to your persistence flags; omit Prisma.sql specifics. Direct test exists — cite it in any port's CI.
