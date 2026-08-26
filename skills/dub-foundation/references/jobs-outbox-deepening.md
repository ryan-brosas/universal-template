<!-- capsule-v2 -->
# Job outbox deepening — how does the jobs framework guarantee dispatch when QStash publish fails, and what does the retry cron do with exhausted jobs?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What is the exact published-vs-deferred contract inside dispatchJobs, and how does the minute-cron replay rows without double-publishing?

## defineJob/dispatchJobs + queue/retry cron: fail-open to DB, delete-on-publish
**Path/Symbol:** `apps/web/lib/jobs/index.ts:dispatchJobs` (:322-411), `persistBackgroundJobs`/`deferJobs` (:200-245), `buildReplayRequest` (:150-176), `defineJob` (:413-465); retry cron `apps/web/app/(ee)/api/cron/queue/retry/route.ts:GET` (:23-160).
**Signature:** `DispatchResult = {status:"published",messageId} | {status:"deferred",backgroundJobId}`; envelope `{name (kebab-case `-job`), dispatchedAt, payload:unknown}`; QSTASH_BATCH_CHUNK_SIZE=100; MAX_ATTEMPTS=10.
**Data Shape:** dedup ids are caller-scoped with `,jobName` appended (`buildJobDeduplicationId` :70-78) so two different jobs sharing a caller key never collide; labels append the job name for log filtering.

### Decisive source
```ts
// Persist jobs that could not be published to QStash. The
// /api/cron/queue/retry cron republishes them and deletes the rows on success.
const responses = await publishJobsToQStash(inputChunk);
...
if (!isPublishSuccess(response)) failedInputs.push(input);
... const deferredResults = await deferJobs(failedInputs);   // prisma.job.createMany
```
(jobs/index.ts :199-347)
```ts
const acquired = await redis.set(LOCK_KEY, "1", { nx: true, ex: LOCK_TTL_SECONDS });
// TTL must be ≥ cron maxDuration (600s in vercel.json) so the lock cannot expire
// while a run is still alive and allow a concurrent minute-cron invocation
responses = await qstash.batchJSON(entries);   // entries = buildReplayRequest(job, now)
...
if (publishedJobIds.length > 0)
  await prisma.job.deleteMany({ where: { id: { in: publishedJobIds } } });
```
(queue/retry/route.ts :17-121)

**Flow:** dispatch: per 100-chunk publish → per-row response check → successes return `published`; QStash-rejected or thrown rows fall through TWO safety nets — first defer just the failed subset, and if THAT persist fails, log `jobs.dispatch_lost` and only then count failure → replay request rebuilds the original envelope with the ORIGINAL dispatchedAt and converts delay/notBefore into a future `notBefore` from scheduledFor. Retry cron: fixed-value NX lock whose TTL equals maxDuration (600s) so overlapping minute-crons can't double-run → take 100 oldest with attempts<10 → one batchJSON → per-row split: published ⇒ row DELETED (at-least-once achieved by deletion-after-publish), non-success or batch throw ⇒ increment attempts + store lastError(1000 chars); crossing MAX_ATTEMPTS logs `jobs.retry_exhausted` for manual intervention and is excluded by the WHERE thereafter.
**Invariant:** (1) DB-persist happens ONLY after publish fails — the happy path never pays a write; (2) deletion is keyed to a VERIFIED messageId per row, so partial batch success deletes exactly those rows; (3) attempts increments are the poison-pill guard — no exponential backoff, just exclusion at 10 plus loud logging; (4) replay preserves the original envelope timestamp so consumer-side age checks stay honest.
**Probe:** deterministic probe: `grep -c 'isPublishSuccess' apps/web/lib/jobs/index.ts 'apps/web/app/(ee)/api/cron/queue/retry/route.ts' | paste -sd' '` = 2 files; `grep -n 'MAX_ATTEMPTS = 10\|LOCK_TTL_SECONDS = 600' 'apps/web/app/(ee)/api/cron/queue/retry/route.ts'` = :14-15. No upstream unit suite covers these helpers directly (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "dispatchJobs", limit: 5 });
```

## Verdict
Adopt the publish-first/defer-on-failure outbox with verified-messageId deletion and attempt-capped replay. Adapt table shape and lock TTL to your cron cadence. Omit queue-name routing if you have no named queues.
