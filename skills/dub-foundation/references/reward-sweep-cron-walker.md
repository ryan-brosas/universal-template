<!-- capsule-v2 -->
# Reward sweep cron — event-differentiated update/notify ladder with cursor self-chaining

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** How does one cron route apply a reward to (or remove it from) every enrollment in a group without missing or double-notifying partners?

## POST /api/cron/rewards/process batch walker
**Path/Symbol:** `apps/web/app/(ee)/api/cron/rewards/process/route.ts:POST` (withCron-wrapped, :20-217).
**Signature:** `withCron(async ({rawBody}) => Response)`; body parsed by rewardJobSchema.
**Data Shape:** pages of ≤300 ProgramEnrollments ordered by `id asc`, filtered to active-ish statuses (`status notIn INACTIVE_ENROLLMENT_STATUSES`) and — for updates only — rows already carrying the reward id column; cursor = last-seen enrollment id.

### Decisive source
```ts
switch (event) {
  case "reward-created":
    data = { [rewardIdColumn]: reward.id };
    break;

  case "reward-updated":
    where = { [rewardIdColumn]: reward.id };
    break;

  case "reward-deleted":
    data = { [rewardIdColumn]: null };
    break;
}
```
(route.ts :90-102)

and

```ts
let shouldNotify = !data;

// Only when event is "reward-created" or "reward-deleted"
if (data) {
  const { count } = await prisma.programEnrollment.updateMany({
    where: {
      id: {
        in: programEnrollments.map(({ id }) => id),
      },
    },
    data: {
      ...data,
    },
  });

  shouldNotify = count > 0;
}
```
(:148-165)

**Flow:** parse → resolve reward + group (missing ⇒ logAndRespond skip) → isStaleRewardVersion gate BEFORE any work → build per-event arms: created ⇒ write rewardId onto enrollments; updated ⇒ SELECT-only (where rewardIdColumn=reward.id) since values live in the reward row itself; deleted ⇒ write null → page 300 by id-cursor (`id gt startAfterProgramEnrollmentId`) → if data-arm: batched updateMany, notify only when count>0; updated: notify unconditionally → notify ONLY ACTIVE-status users via notifyPartnerRewardChange keyed `partner-reward-change-<rewardId>-<batchNumber>-<version>` → re-enqueue with advanced cursor + incremented batchNumber (same version) → terminal page: for deleted events hard-delete the Reward row swallowing Prisma P2025 as success.
**Invariant:** the updated-arm never rewrites enrollments (denormalized ids unchanged) so its batches must NOT skip notification even when zero writes occur — that's why `shouldNotify = !data` seeds true only for the select-only arm; the P2025-swallow exists so a retried final batch can still resend notifications instead of 500-ing on an already-deleted reward. Staleness check runs per-batch, so a mid-sweep edit aborts at the NEXT batch boundary, not retroactively.
**Probe:** deterministic probes (repo root): `grep -n 'take: 300' "apps/web/app/(ee)/api/cron/rewards/process/route.ts"` → :145; `grep -n 'orderBy' "apps/web/app/(ee)/api/cron/rewards/process/route.ts"` → :142; `grep -n 'shouldNotify' "apps/web/app/(ee)/api/cron/rewards/process/route.ts"` → :149/:164/:167; `grep -n 'P2025' "apps/web/app/(ee)/api/cron/rewards/process/route.ts"` → :206; `grep -n 'partner-reward-change-' "apps/web/app/(ee)/api/cron/rewards/process/route.ts"` → :179; `grep -n 'notIn: INACTIVE_ENROLLMENT_STATUSES' "apps/web/app/(ee)/api/cron/rewards/process/route.ts"` → :108.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "logAndRespond", limit: 5, fields: ["signature", "name", "file"] });
```
(the route's own POST is the withCron wrapper; sibling capsules `cron-dual-auth` cover the auth shell.)

## Verdict
Adopt the three-arm switch, count-gated vs unconditional notification split, id-cursor chaining at 300/batch, and P2025-as-success deletion. Adapt statuses/ORM. Omit nothing.
