<!-- capsule-v2 -->
# Seed task chunking & fan-out split — how does one giant recompute task become bounded child tasks before it ever touches a lock?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Where in the worker lifecycle are oversized tasks split, and when does splitting apply to link-traversal plans vs whole-table plans?

## splitLargeComputedTask / splitLargeSeedTask / splitSeedRecordDtos
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/worker/ComputedUpdateWorker.ts` — `splitLargeComputedTask` (:1149–1180), `splitLargeSeedTask` (:1179–1208), pure helpers `splitSeedRecordDtos` (:113–150), `splitComputedTaskForSeedRecordLimit`, `resolveEffectiveMaxSeedRecordsPerTask`, fanout gate (module tail); config `maxSeedRecordsPerTask` + `fanoutDirtyRecordsThreshold` on ComputedUpdateOutboxConfig.
**Signature:** `splitComputedTaskForSeedRecordLimit(task, max): Chunk[]` (empty array = no split needed); chunks preserve plan identity (`runId`, `originRunIds`, run-step counters recomputed per chunk).
**Data Shape:** SeedRecordChunk `{seedRecordIds: string[], extraSeedRecords: {tableId, recordIds[]}[]}`; greedy fill up to `max(1, trunc(max))`.

### Decisive source
```ts
const chunks = splitComputedTaskForSeedRecordLimit(task, maxSeedRecordsPerTask);
if (chunks.length === 0) return ok(false);          // not oversized — continue normal path
for (const chunk of chunks) {
  const enqueueResult = await this.outbox.enqueueOrMerge(chunk, context);
  if (enqueueResult.isErr()) return err(enqueueResult.error);
}
const doneResult = await this.outbox.markDone(task, context);
...
this.logger.info('computed:worker:large_task_split', {
  taskId: task.id, chunkCount: chunks.length,
  seedRecordCount, maxSeedRecordsPerTask,
  configuredMaxSeedRecordsPerTask: this.outboxConfig.maxSeedRecordsPerTask,
  fanoutDirtyRecordsThreshold: this.outboxConfig.fanoutDirtyRecordsThreshold, ...logContext });
```

**Flow:** BEFORE deserialization/locks, an oversized task is replaced by N record-bounded children (each ≤ maxSeedRecordsPerTask) and the parent is markDone'd — children inherit run accounting so progress stays coherent. The FAN-OUT variant splits even small-seed tasks when dirtyStats show a large affected population AND the plan uses linkTraversal edges; whole-table (`allTargetRecords`) plans never fan-out-split (splitting doesn't shrink whole-table work), and a split that would create too many tiny chunks is refused.
**Invariant:** Splitting must happen BEFORE lock acquisition — a huge task holding record/table advisory locks while chunking would serialize the whole queue behind it. Children must carry the parent's run identity; dropping run counters orphans stage tracking. "Too many chunks" refusal prevents unbounded enqueue amplification.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/worker/ComputedUpdateWorker.spec.ts` describe('seed record chunking') :169 ('keeps 4k seed tasks whole by default', :190 'fanout-splits linkTraversal plans with large dirtyStats and few seeds', :222 'does not fanout-split when plan has allTargetRecords edges', :250 'does not fanout-split when seed set would create too many chunks') + :831 'splits large computed tasks into smaller child tasks before acquiring locks'.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "splitLargeComputedTask splitComputedTaskForSeedRecordLimit fanoutDirtyRecordsThreshold", limit: 10 });
```

## Verdict
Adopt pre-lock size-based replacement with run-identity-preserving children, the traversal-only fan-out gate, and the too-many-chunks refusal; adapt threshold names/values to host config; omit teable's outbox merge-on-enqueue interplay if your queue lacks dedupe keys.
