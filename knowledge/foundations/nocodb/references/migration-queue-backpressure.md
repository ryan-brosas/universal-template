<!-- capsule-v2 -->
# Migration queue backpressure — why must the enqueue gate watch queue.size, not queue.pending?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does a while(true) producer feeding a PQueue actually bound its unprocessed backlog?

## The pending-vs-size gate, and the NOT-IN planner trap under it
**Path/Symbol:** `packages/nocodb/src/modules/jobs/migration-jobs/nc_job_010_soft_delete_column.ts:job` (:186-224) with the fixed gate at :189-195 and getModelsQuery comment (:662-675); the OLD buggy gate survives in `nc_job_005_order_column.ts:165-169` and `nc_job_014_link_order_column.ts:156-160` (`queue.pending > PARALLEL_LIMIT * 2`); `_001/:541-544` gates on `pending > parallelLimit`.
**Signature:** `if (queue.size > concurrency * 2) { await sleep(1000); continue; }`.
**Data Shape:** PQueue semantics — `.size` = queued-but-not-started tasks; `.pending` = currently-executing count (≤ concurrency by definition).

### Decisive source
```ts
const queue = new PQueue({ concurrency });
while (true) {
  // PQueue.pending is capped at concurrency; waiting tasks accumulate
  // in .size. Guard on size to actually bound unprocessed backlog.
  if (queue.size > concurrency * 2) {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    continue;
  }
  this.processingModels = this.processingModels.filter((m) => m.processing);
  const models = await this.getModelsQuery(ncMeta, concurrency); // .limit(concurrency * 10)
  if (!models?.length) break;
  for (const model of models.splice(0)) {
    this.processingModels.push({ fk_model_id: model.id, processing: true });
    queue.add(() => wrapper(model)).catch(logAndContinue);
  }
}
await queue.onIdle();
```

**Flow:** loop → pause 1s whenever more than 2×concurrency tasks are WAITING (not running) → prune finished entries from the in-memory processing set → fetch the next page EXCLUDING ids already in the temp table AND in the in-flight set → enqueue wrappers → break when a page comes back empty → onIdle before disabling upgrader mode.
**Invariant:** gating on `.pending` bounds nothing once concurrency saturates — every iteration keeps fetching pages until the DB cursor exhausts, so the queue (and its memory) grows to the whole fleet; that is precisely what the older `_005`/`_014` jobs still do. The exclusion query is equally load-bearing: with a temp ledger of 200k+ rows, PG's `NOT IN (subquery)` planned into 10+ minute anti-joins; `NOT EXISTS … whereRaw(t.fk_model_id = models.id)` plans cleanly against the fk index — a porter copying "NOT IN" for familiarity reimports the outage behind issue #12379-era pain.
**Probe:** no unit test upstream. Source-grounded probe: comment lines :190-191 state the size/pending distinction verbatim; `_005:166` shows the unfixed twin; getModelsQuery comment :662-664 records the PG planner measurement.
**Coverage caveat:** no in-repo tests; source-grounded.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "PQueue queue.size concurrency backpressure getModelsQuery whereNotExists", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the `.size` gate + NOT EXISTS anti-join for any paged worker-pool over a resume ledger; adapt thresholds (2× is arbitrary but must exceed concurrency); omit the SQLite-forced-concurrency-1 branch only if your fleet has no SQLite.
