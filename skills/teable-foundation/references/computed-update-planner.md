<!-- capsule-v2 -->
# Computed-field update planning — how does teable turn a record change into an ordered set of recompute steps across tables?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does a dependency-graph planner decide which computed fields to recompute after an insert/update/delete, in what order, and with what propagation mode, so a porter gets the affected-set and cycle handling right?

## Impact → affected-field-set → ordered update steps
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/ComputedUpdatePlanner.ts` — `ComputedUpdatePlanner.plan` (284–305), `.planStage` (357–970), `.resolveBeforeImageRequirements` (307–355); helpers `splitSeedGroupsForPlan` (1377–1398), `topoSort` (1400–1443), `findCycleParticipantFieldIds` (1445+), `computedFieldTypes`/`isComputedFieldType` (1347–1356).
**Signature:** `plan(context: UpdateContext, executionContext?, options?): Promise<Result<ComputedUpdatePlan, DomainError>>`; `planStage(context: PlanStageContext, executionContext?, options?): Promise<Result<ComputedUpdatePlan, DomainError>>`.
**Data Shape:** `UpdateContext = {table, changedRecordIds, changedFieldIds, changeType:'insert'|'update'|'delete', impact?, cyclePolicy:'error'|'skip'}`. `DirtyPropagationMode = 'linkTraversal'|'allTargetRecords'|'conditionalFiltered'`. Plan carries `updateSteps[]`, `cycleInfo`, `beforeImageRequirements`, `affectedFieldIds`.

### Decisive source
```ts
// INSERT seeds ALL table fields so every computed field (even dependency-free) gets initial values
const planningSeedFieldIds = context.changeType === 'insert' && context.table
  ? context.table.getFields().map((f) => f.id())
  : collectImpactSeedFieldIds(context.changedFieldIds, context.impact);
// DELETE: source fields depended on by conditionalLookup/conditionalRollup in other tables become value seeds
if (context.changeType === 'delete') for (const edge of edges) {
  if (edge.kind !== 'cross_record' || !edge.fromTableId.equals(context.seedTableId)) continue;
  if (edge.semantic !== 'conditional_rollup_source' && edge.semantic !== 'conditional_lookup_source') continue;
  valueSeedFieldIds.set(edge.fromFieldId.toString(), edge.fromFieldId);
}
// link relation change: refresh symmetric link fields + their dependents (cross-base symmetric mirrors options)
if (impact.includesLinkRelation) { /* add symmetricFieldId edges, reverse relationship */ }
```
**Flow:** `plan` delegates to `planStage` with the table as seed. `planStage`: compute impact seed fields → for INSERT seed all fields → load the dependency graph (`graph.load(baseId, {requiredFieldIds, tableProvisionStates:['ready'], scopedPendingTableIds})`) → `resolveUpdateImpact` → for DELETE add conditional cross-record source seeds → add symmetric link edges for link-relation changes → collect direct affected field ids via value/link edges (include-seeds-always only on INSERT) → topologically sort the affected set (Tarjan SCC for cycles) → emit `updateSteps` in dependency order, honoring `cyclePolicy` ('skip' drops cycle fields, 'error' fails) → derive before-image requirements for conditionalFiltered mode. `splitSeedGroupsForPlan` picks the primary seed table (preferred or first non-empty) and demotes the rest to `extraSeedRecords`.
**Invariant:** INSERT seeds every table field (not just changed ones) so dependency-free computed fields get initial values; DELETE promotes conditional cross-record source fields to value seeds so conditional fields in other tables recalc; symmetric link fields are always refreshed on link-relation changes and their dependents traversed; the update order is a topological sort of the dependency graph and cycle participants are handled per `cyclePolicy`; the affected set is computed from the dependency graph, never from a naive field scan.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/__tests__/ComputedUpdatePlanner.spec.ts` — `"propagates link relation changes from lookup fields into dependent formulas"` (:56), `"plans symmetric link updates from impact link fields when changed fields are empty"` (:489), `"skips cycle fields for delete while keeping ordered updates"` (:627), `"uses conditionalFiltered mode when updating non-filter field (Price)"` (:1133), `"uses allTargetRecords mode when updating filter field (Category)"` (:1284).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "ComputedUpdatePlanner planStage resolveUpdateImpact", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the impact→affected-set→topo-sorted-steps planning shape, the INSERT-seeds-all / DELETE-promotes-conditional-source rules, symmetric-link refresh, Tarjan cycle detection with `cyclePolicy`, and the propagation-mode ladder (linkTraversal/allTargetRecords/conditionalFiltered). Adapt the dependency-edge semantics and field-type set to your domain. Omit teable's formula-engine internals and the outbox worker (that is `computed-update-outbox.md`). Caveat: `ComputedUpdatePlanner.ts` is 2,036 lines; the cited ranges are the planning core — the `planStage` continuation (558–970) holds the step-building details a porter should read before porting.
