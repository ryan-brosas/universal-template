<!-- capsule-v2 -->
# Job dispatch — publish-over-QStash with a DB outbox fallback

**Source:** dub AGPL-3.0-or-later (EE dirs separately licensed) `main@873edc5a9727317513c966b8d9b9171794fc89f8`; Codebase Memory `dub`. **Question:** How do you dispatch background jobs through a hosted queue so that a failed publish never loses the job?

## defineJob / dispatchJobs
**Path/Symbol:** `apps/web/lib/jobs/index.ts:defineJob` (396–446), `dispatchJobs` (275–394), `persistBackgroundJobs` (201–235), `buildQStashJobRequest` (121–155).
**Signature:** `defineJob<TSchema extends z.ZodType>({ name, schema, defaults?, handle }): { name, execute(payload), dispatch(payload, options?), dispatchBatch(payloads, getOptions?) }`.
**Data Shape:** wire envelope `{ name, dispatchedAt, payload }` (`jobEnvelopeSchema`, :89–93) validated against `jobNameSchema` = kebab-case ending `-job` (:60–65). Dispatch options: `{ delay, notBefore, deduplicationId, retries, flowControl, label, queue }`. `DispatchResult = { status:"published", messageId } | { status:"deferred", backgroundJobId }`.

### Decisive source
```ts
// per-chunk publish; any failure falls through to the DB outbox
for (const inputChunk of chunk(inputs, QSTASH_BATCH_CHUNK_SIZE)) {   // 100/batch
  try {
    const responses = await publishJobsToQStash(inputChunk);         // withQStashRetry: 1+3 tries, exp backoff 1s*2^n
    const failedInputs = /* responses[i] not isPublishSuccess */;
    if (failedInputs.length > 0) await deferJobs(failedInputs);      // persist -> prisma.job rows
  } catch (error) {
    try { await deferJobs(inputChunk); }                             // whole chunk deferred
    catch (persistError) { /* log jobs.dispatch_lost, flush, rethrow */ }
  }
}
// deferJobs -> persistBackgroundJobs: id=createId({prefix:"job_"}), scheduledFor derived
// from notBefore (epoch s) or Date.now()+delay*1000; replayOptions stored for republish
```

**Flow:** `defineJob` validates the name once at definition time → `dispatch()` merges per-job `defaults` under call options → `dispatchJobs` chunks at 100 → single item uses `qstash.publishJSON/enqueueJSON`, many use `qstash.batchJSON` → each publish retried up to 3 extra times with exponential backoff (`withQStashRetry` :102–119) → any response without a string `messageId` (or a thrown error) is persisted into the `job` Prisma table → the `/api/cron/queue/retry` cron republishes persisted rows via `buildReplayRequest` (:157–186, recomputes `notBefore` from `scheduledFor > now`) and deletes them on success.
**Invariant:** a dispatch either returns `published` (QStash accepted) or `deferred` (row persisted) — a job is never silently dropped; only if BOTH publish and persist fail does `dispatchJobs` log `jobs.dispatch_lost` and rethrow. `deduplicationId` and `label` are namespaced per job (`${id},${name}` / `${label},${name}` :72–86) so cross-job collisions can't suppress each other.
**Probe:** no dedicated unit test exists for the dispatcher (repo tests cover analytics/webhooks/misc utils). Source-grounded probe: `search_graph` project `dub` resolves `defineJob`/`dispatchJobs`; port with your own test asserting a failing publish produces a `prisma.job` row with the original payload + options.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "defineJob dispatchJobs persistBackgroundJobs", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the envelope schema + kebab-case `-job` naming, the published|deferred result contract, the DB-outbox-on-publish-failure pattern, and per-job namespacing of dedup/label; adapt the transport (QStash → SQS/Redis stream), the outbox table, and batch size. Omit the Vercel/ngrok endpoint URL construction (`APP_DOMAIN_WITH_NGROK`). Caveat: no direct upstream test for this seam.
