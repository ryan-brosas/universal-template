<!-- capsule-v2 -->
# Reward sweep job envelope — versioned QStash publication with self-chaining batches

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** What exactly rides in a reward-processing job, and how do batchNumber/version compose the idempotency and staleness keys?

## rewardJobSchema + queueRewardProcessing
**Path/Symbol:** `apps/web/lib/api/rewards/queue-reward-processing.ts:rewardJobSchema` (:8-31) + `queueRewardProcessing` (:35-81).
**Signature:** `queueRewardProcessing(params: RewardJob): Promise<QStash publish response>`; throws a user-facing generic Error on any failure.
**Data Shape:** `{event: "reward-created"|"reward-updated"|"reward-deleted", groupId, occurredAt, version?=1, batchNumber?=1, startAfterProgramEnrollmentId?, rewardSnapshot:{id,event,description,activityDescription?}}`; published to `/api/cron/rewards/process` via qstash.publishJSON.

### Decisive source
```ts
const version =
  params.version !== undefined
    ? params.version
    : await incrementRewardVersion({
        groupId: params.groupId,
        event: params.rewardSnapshot.event,
      });
```
(queue-reward-processing.ts :38-44)

and

```ts
if (!response?.messageId) {
  throw new Error(
    "We couldn't start reward processing right now. Please try again in a few moments.",
  );
}
```
(:55-59)

**Flow:** caller (create/update/delete reward actions) omits version ⇒ fresh incrementRewardVersion mint; recursive cron calls PASS version through so every batch of one sweep shares it → publishJSON with method POST → missing/absent messageId ⇒ throw (QStash accepted-but-unconfirmed treated as failure) → catch path logs structured axiom telemetry (`publishJSON.failed` with correlation event/groupId/rewardId), flushes logger, re-throws the SAME generic message.
**Invariant:** batchNumber is NOT an idempotency key for Dub itself — schema comment says "Used as a idempotency key for Resend" (the email provider); Dub-side dedupe composes `partner-reward-change-<rewardId>-<batchNumber>-<version>`. The version-passthrough rule is what makes mid-sweep staleness detection possible; a porter who lets each batch re-mint versions defeats the ledger.
**Probe:** deterministic probes (repo root): `grep -n '"Used as a idempotency key for Resend."' apps/web/lib/api/rewards/queue-reward-processing.ts` → :23; `grep -n 'params.version !== undefined' apps/web/lib/api/rewards/queue-reward-processing.ts` → :39; `grep -n '/api/cron/rewards/process' apps/web/lib/api/rewards/queue-reward-processing.ts` → :47/:66; callers: `grep -rln 'queueRewardProcessing' apps/web/lib/actions/partners` → create-reward.ts, update-reward.ts, delete-reward.ts.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "queueRewardProcessing", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the envelope shape, first-call mints / recursion passes version, and messageId-or-throw. Adapt QStash to host queue. Omit nothing.
