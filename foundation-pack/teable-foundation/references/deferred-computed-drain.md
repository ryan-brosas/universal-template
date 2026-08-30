<!-- capsule-v2 -->
# Deferred computed drain — how do streaming bulk writes skip per-batch recomputation and settle it exactly once at the end?

**Source:** teable AGPL `develop@06a4461e`. **Question:** insertManyStream/updateManyStream accept deferComputedUpdates — what are the two terminal paths (enqueue vs fire-and-forget) and their failure semantics?

## accumulate records/impact across batches → enqueueSeedTask OR afterCommit void-run; failures warn, never throw
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `insertManyStream` (:1864–1974, terminal at :1954–1971), `updateManyStream` accumulation maps (:2498–2520, terminal :2813–2862), `enqueueDeferredComputedUpdateMany` (:2007–2066), `scheduleDeferredComputedUpdateMany` (:1976–2005), `scheduleDeferredComputedUpdateManyByIds` (:3009–3047), transaction-strip idiom `const computeContext = {...context}; delete computeContext.transaction;` (:1982–1983, :2056–2057, :2993–2995, :3018–3019).
**Signature:** options `{skipComputedUpdates?, deferComputedUpdates?, enqueueDeferredComputedUpdates?}`.

### Decisive source
```ts
if (deferComputed && allInsertedRecords.length > 0) {
  const computedResult = enqueueDeferredComputedUpdates
    ? await this.enqueueDeferredComputedUpdateMany(context, table, allInsertedRecords, ...)
    : this.scheduleDeferredComputedUpdateMany(context, table, allInsertedRecords, ...);
  if (computedResult.isErr()) return err(computedResult.error);
}
// schedule variant:
const run = () => { void this.runComputedUpdateMany(...).then(result => {
  if (result.isErr()) this.logger.warn('computed:deferred:failed', {...}); }); };
if (context.transaction?.afterCommit) context.transaction.afterCommit(run); else run();
```

**Flow:** while batching, pass `skipComputedUpdates:true` to every inner insertMany/updateMany call and ACCUMULATE records (insert-stream) or affected ids + value/link field unions + extra seeds + first-wins before-images (update-stream) → after the LAST batch, either (a) enqueue one merged seed task and await its result, or (b) register a void background run that logs-but-swallows failures.
**Invariant:** The three-flag ladder is load-bearing: `skip` ⊃ `defer`; defer WITHOUT enqueue = fire-and-forget (errors only logged — chosen when callers cannot handle late failures); defer WITH enqueue awaits enqueue success so durable delivery is guaranteed before the API returns. Before-image maps keep FIRST occurrence (`if (beforeImageByRecordId.has(key)) continue`, :2718–2721) because re-updating a record inside one stream makes its earliest pre-image the correct undo base. Impact unions dedupe via Maps so the single terminal seed covers every touched field once.
**Probe:** update.spec.ts :1768 ('returns Err when the insert stream throws a domain error') pins stream error passthrough; :1806 restore-style skip behavior.
**Coverage caveat:** terminal-path unit tests exercise enqueue/schedule indirectly via stream specs — noted.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "deferComputedUpdates insertManyStream enqueueDeferredComputedUpdateMany scheduleDeferred", limit: 8 });
```
## Verdict
Adopt for high-throughput ingest: accumulate minimal trigger facts during streaming, settle derived work once at the end, choose awaited-enqueue vs logged-fire-and-forget explicitly per reliability contract.
