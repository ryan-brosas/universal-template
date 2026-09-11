<!-- capsule-v2 -->
# Dual-consumer import fan-out — how do row import and link import share ONE paused stream and ONE PQueue, and why does nothing ever throw?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does `importData` interleave per-row transforms and M2M link extraction over the same record stream without losing records or failing the job?

## Two 'data' listeners, one shared queue, end-phase flush ladder
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/at-import/helpers/readAndProcessData.ts` — `importData` (:110-336), `importLTARData` (:338-577), `readAllData` producer (:31-108).
**Signature:** `importData(context, {...}): Promise<{nestedLinkCount, importedCount}>`; `importLTARData(context, {...}): Promise<number>`; both take the SAME `dataStream: Readable` and `queue: PQueue` plus shared `idMap: Map<string,number>`, `idCounter: Record<string,number>`.
**Data Shape:** stream chunks are JSON strings `{_atId, ...fields}`; knobs `BULK_DATA_BATCH_COUNT=10`, `BULK_DATA_BATCH_SIZE=20*1024` bytes, `BULK_LINK_BATCH_COUNT=500`, `BULK_PARALLEL_PROCESS=2`, `STREAM_BUFFER_LIMIT=100`, `QUEUE_BUFFER_LIMIT=20` (all env-tunable).

### Decisive source
```ts
// importData: create PAUSED stream, start producer fire-and-forget, then fan out
const dataStream = new Readable({ read() {} });
dataStream.pause();
readAllData({...}).catch((e) => { logger.error(e); logWarning(`...${e}`); }); // no await
return new Promise(async (resolve) => {
  const queue = new PQueue({ concurrency: BULK_PARALLEL_PROCESS }); // ONE queue
  const ltarPromise = importLTARData(context, { ..., dataStream, queue,
    idMap, idCounter, ... }).catch((e) => { logger.error(e); logWarning(...); });
  ...
  dataStream.on('data', async (record) => {          // consumer #1: rows
    counter.streamingCounter--;
    queue.add(() => new Promise(async (resolve) => {
      try {
        if (!idMap.has(rid)) idMap.set(rid, idCounter[table.id]++);
        const r = await nocoBaseDataProcessing_v2(syncDB, table, { id: rid, fields });
        tempData.push({ ...r, id: idMap.get(rid) });
        if (tempCount >= BULK_DATA_BATCH_COUNT) {
          if (sizeof(tempData) >= BULK_DATA_BATCH_SIZE) {   // count AND bytes
            await services.bulkDataService.bulkDataInsert(context, { body:
              tempData.splice(0, tempData.length), skip_hooks: true,
              foreign_key_checks: !!source.isMeta(), allowSystemColumn: true,
              undo: true });
          } }
        if (queue.size < QUEUE_BUFFER_LIMIT / 2) dataStream.resume();
        resolve(true);
      } catch (e) { logger.error(e); logWarning(...);
        if (queue.size < QUEUE_BUFFER_LIMIT / 2) dataStream.resume();
        resolve(true); }                                     // swallow per-task
    }));
    if (queue.size >= QUEUE_BUFFER_LIMIT) dataStream.pause();
  });
  dataStream.on('end', async () => {                  // flush ladder
    await queue.onIdle();                              // drain shared queue FIRST
    if (tempData.length > 0) { await bulkDataInsert(...); }
    nestedLinkCount = (await ltarPromise) as number;   // THEN link phase result
    resolve({ importedCount, nestedLinkCount });       // even the catch RESOLVES
  });
});
// importLTARData: consumer #2 on the SAME stream, resumed only after listeners exist
return new Promise((resolve, reject) => {
  dataStream.on('data', async (record) => { /* bucket mm tuples per junction table */ });
  dataStream.on('end', async () => { await queue.onIdle(); /* flush links */
    resolve(nestedLinkCnt); });
  // resume the stream after all listeners are attached
  dataStream.resume();
});
```

**Flow:** the producer pages Airtable (~100/page) pushing JSON strings; the stream starts PAUSED so early pushes merely buffer. Consumer #1 (rows) attaches synchronously inside `importData`'s executor; consumer #2 (links) attaches only after its meta fetches (`getTableWithAccessibleViews` per LTAR column), then calls `dataStream.resume()` — flow begins with BOTH listeners guaranteed registered, so every chunk reaches row-transform AND link-bucketing exactly once each (Node delivers each 'data' event to all listeners; attachment order fixes execution order). Both consumers enqueue work onto the ONE `PQueue(concurrency=2)`, so row inserts and link-tuple buffering share a single admission budget and the queue-depth backpressure gates stay meaningful regardless of which side is slow. Link rows land in `assocTableData[junctionTableId]` buckets flushed at 500, mapping airtable ids through the SHARED `idMap` — ids for not-yet-imported related records are allocated eagerly from the related table's counter, which is what lets forward references resolve later. Termination is a fixed ladder: producer always `push(null)` (even on page error), each consumer's 'end' runs `queue.onIdle()` then flushes its remainder; `importData`'s end additionally awaits `ltarPromise` before resolving.
**Invariant:** (1) NOTHING THROWS: producer runs detached with `.catch`; every queued task try/catches and resolves anyway (resume included in the catch path); the final 'end' catch still RESOLVES with partial counts instead of rejecting — a failed import degrades to warnings while the job stays green (the caller-side tier policy is the at-import-failure-policy capsule). Corollary: `nestedLinkCount` can be `undefined` after an LTAR rejection because the pre-caught promise resolves void — callers adding it get NaN unless guarded. (2) One queue, two feeders: moving either consumer onto its own queue doubles effective parallelism past `BULK_PARALLEL_PROCESS` and breaks the hysteresis assumptions documented in airtable-backpressure. (3) Batch flush requires count≥10 AND bytes≥20KB — count alone is insufficient because Airtable row widths vary wildly; the trailing partial batch flushes ONLY in 'end'. (4) `insertedAssocRef[fk_mm_model_id]` is claimed BEFORE the awaited assoc-meta fetch (:408) — concurrent re-entry can't double-create a junction plan mid-await. (5) Bulk inserts run with `skip_hooks:true` (+ `foreign_key_checks` only for meta sources): import traffic must not fire webhooks/audits. (6) After all tables, the PROCESSOR (not this file) resets pg sequences: `setval(pg_get_serial_sequence(tbl,'id'), MAX(id))` per migrated table — explicit-id bulk inserts leave serials stale everywhere else.
**Probe:** no unit test upstream; file is graph parse_partial (ranges 45-47/136-138/373-375) — claims verified by whole-file source read. Deterministic probes: `readAndProcessData.ts:168` immediate `.pause()`; `:186-208` ltarPromise sharing `{dataStream, queue}` with `.catch`; `:574-575` comment + `resume()` after listener attach; `:315` `await ltarPromise` inside 'end'; `:103` unconditional `dataStream.push(null)`.
**Coverage caveat:** parse_partial file — source read directly; no tests cover this seam.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "importData importLTARData dataStream queue onIdle insertedAssocRef idMap idCounter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fan-out shape for any streaming migration with two derived workloads off one source: one paused Readable, N listeners attached before resume, ONE shared admission-controlled queue, per-task swallow-and-resume error policy, onIdle+flush termination. Adapt chunk format, batching thresholds, and the eager id-allocation scheme to your id strategy. Omit the Airtable `_atId` bookkeeping and the pg sequence reset if your inserts go through normal auto-increment paths.
