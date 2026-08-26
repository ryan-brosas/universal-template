<!-- capsule-v2 -->
# Sync dirty-seed cascade — how does synchronous recomputation chase cross-record fallout without re-updating fields it already fixed?

## stage loop: execute → collectDirtySeedGroups → planNextStage → filter updatedFieldIds → repeat until no steps survive
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/strategies/SyncInTransactionStrategy.ts` (whole file 189L) — main loop (:70–133), dedup set + comment (:62–65 "Without this, computed fields in the dependency chain would be updated multiple times"), dirty collection (:101–105), next-stage planning (:142–170, changeType fold insert/delete→update :160–161, impact `{valueFieldIds: seedFieldIds, linkFieldIds: []}` :163–166), helpers (:173–189).
**Signature:** `execute(updater, plan, context): Promise<Result<ComputedUpdateResult | undefined>>`; interface `IUpdateStrategy` (`IUpdateStrategy.ts` :21–36: `mode`, `execute`, `scheduleDispatch`).

### Decisive source
```ts
const updatedFieldIds = new Set<string>();
while (currentPlan.steps.length > 0) {
  await updater.acquireLocks(currentPlan, context, {...});
  const stageResult = await updater.execute(currentPlan, context, run, { collectChanges: true });
  allChangesByStep.push(...stageResult.value.changesByStep);
  for (const step of currentPlan.steps)
    for (const id of step.fieldIds) updatedFieldIds.add(id.toString());   // mark BEFORE replan
  const seedGroups = await updater.collectDirtySeedGroups(context, collectStepTableIds(currentPlan));
  const nextSeedFieldIds = collectStepFieldIds(currentPlan);
  const nextPlan = await this.planNextStage(currentPlan, context, nextSeedFieldIds, seedGroups);
  const filteredSteps = nextPlan.value.steps
    .map(step => ({...step, fieldIds: step.fieldIds.filter(id => !updatedFieldIds.has(id.toString()))}))
    .filter(step => step.fieldIds.length > 0);
  if (!filteredSteps.length) break;
  currentPlan = {...nextPlan.value, steps: filteredSteps};
}
```

**Flow:** execute the initial topo-sorted plan inside the current transaction → ask the updater which (table, records) became DIRTY by those writes → replan with the executed fields as new changed-fields seeds → strip every already-updated field from the fresh steps → loop until nothing remains.
**Invariant:** THREE facts that break naive ports: (1) The dirty-set comes from POST-EXECUTE observation (`collectDirtySeedGroups` reads actual dirtied rows), not from graph edges alone — conditional rollups whose filters matched differently than predicted are still caught because they really changed. (2) `updatedFieldIds` filtering is what turns the planner's conservative re-seeding into a fixpoint instead of an infinite loop; without it every stage re-plans the previous stage's outputs (the code comment pins exactly this). (3) Follow-up stages always plan as changeType 'update' even for insert/delete roots (:160–161) — the rows now EXIST (or are gone); only value changes propagate further. Locks re-acquire per stage since each stage may touch different tables.
**Probe:** deterministic whole-file pin at `06a4461e` :70–133; exercised through hybrid spec suite's sync-policy cases.
**Coverage caveat:** no dedicated SyncInTransactionStrategy.spec file — behavior covered via strategy-suite integration — noted.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "SyncInTransactionStrategy collectDirtySeedGroups updatedFieldIds planNextStage", limit: 5 });
```
## Verdict
Adopt whenever derived-data writes can trigger more derived data: observe-dirty→replan→dedup-filter loop with changeType folding, bounded by the already-done set.
