<!-- capsule-v2 -->
# Computed seed dispatch — when does a record write plan-and-execute computed updates inline versus enqueue an outbox seed task, and why does hybrid mode treat deletes differently?

**Source:** teable AGPL `develop@06a4461e`. **Question:** The repository holds planner+updater+strategy+outbox — what is the exact mode×changeType dispatch matrix a porter must reproduce?

## sync ⇒ always inline; hybrid ⇒ inline except delete; async ⇒ never; batch-by-ids ⇒ sync-only unless forceOutbox
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `runComputedUpdate` (:3397–3555, matrix at :3419–3421), `runComputedUpdateMany` (:3557–3717, insert adds ALL table fields :3583–3591), `runComputedUpdateById` (:3719–3856), `runComputedUpdateManyByIds` (:2873–3007, sync-gate + forceOutbox at :2893), `runComputedDeleteUpdateMany` (:3959–4062, sync-ONLY inline at :3975). Tests: update.spec.ts 'hybrid/async computed update' describe (:2002); 'uses returned update ids for updateManyStream computed planning when RETURNING rows are incomplete' (:1118).
**Signature:** helpers return `Result<ComputedUpdateResult | undefined, DomainError>` (undefined ⇒ async path returned nothing).

### Decisive source
```ts
const shouldExecuteInline =
  this.computedUpdateStrategy.mode === 'sync' ||
  (this.computedUpdateStrategy.mode === 'hybrid' && changeType !== 'delete');
// inline:  planStage(planInput) → strategy.execute(updater, plan) → (sync only) publishComputedUpdateEvents
// else:    buildSeedTaskInput({...}) → outbox.enqueueSeedTask → strategy.scheduleDispatch(context)
```
```ts
// batch-by-ids (updateManyStream): inline ONLY in pure sync mode unless forced:
if (this.computedUpdateStrategy.mode === 'sync' && !options.forceOutbox) { ...planStage... }
// For hybrid/async mode, skip planStage to minimize transaction lock hold time.
```

**Flow:** expand changed fields (`expandComputedSeedFieldIds`) → pick lane by the matrix → inline lane runs the dependency-graph planner and executes UPDATE steps inside the current tx, publishing realtime events only when mode is sync → outbox lane builds a minimal seed task (ids + changed fields + before-images + extra seeds + orchestration), enqueues with merge-dedup, then schedules worker dispatch.
**Invariant:** FIVE non-obvious decisions: (1) HYBRID RUNS INSERTS/UPDATES INLINE but defers DELETES — delete propagation fans out to every referencing table, the highest-lock-time plan, so it always rides the worker. (2) Batch-by-ids requires PURE sync for the inline lane because stream batches run inside long transactions where planning could hold locks; `forceOutbox:true` is how defer-flows opt into enqueueing. (3) Insert seeding includes ALL non-link table fields (:3583–3591) so formulas over not-provided columns compute their null-dependent results. (4) Events publish ONLY on the sync lane — hybrid's inline execution publishes nothing (the caller-side mutation events cover it), avoiding duplicate realtime pushes. (5) `scheduleDeferred*` variants clone context and `delete computeContext.transaction` (:1983/:3019) then run under `afterCommit` — computed work must NEVER ride the mutating tx's connection after it returned.
**Probe:** update.spec.ts :2002ff pins hybrid/async lanes; :1118 pins ids-based planning from RETURNING.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "runComputedUpdate shouldExecuteInline enqueueSeedTask scheduleDispatch", limit: 8 });
```
## Verdict
Adopt the matrix verbatim for write-triggered recomputation: mode×changeType decides inline-vs-queue, deletes are the expensive case, batches need explicit force flags, and deferred work strips transaction context.
