<!-- capsule-v2 -->
# Bounty notify-partners cron — how do you fan a new-bounty email campaign out over an unbounded audience without double-sends or provider abuse?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** When a published bounty must announce itself to every eligible partner, what walker shape keeps the campaign resumable, idempotent per batch, and polite to the email provider?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/app/(ee)/api/cron/bounties/notify-partners/route.ts:POST` (:35-244) · publisher `apps/web/app/(ee)/api/bounties/route.ts` waitUntil fan-out (:326-329 predicate, :354-363 publish) · `sendBatchEmail` from `@dub/email` (`packages/email/src/index.ts:sendBatchEmail` :31-60 → `sendBatchEmailViaResend` :74+, Resend Idempotency-Key) · `logAndRespond` from `app/(ee)/api/cron/utils.ts` (:1-21) · audience constants `ACTIVE_ENROLLMENT_STATUSES` (lib/zod/schemas/partners.ts, pass-16).
**Signature:** `POST(req)` — QStash-signed; body `{bountyId: string, startingAfter?: string, batchNumber?: number = 1}`; always responds 200 via logAndRespond (even on "bounty not found", logged at error level) so the queue never retries terminal states.
**Data Shape:** Constants EMAIL_BATCH_SIZE=100, BATCH_DELAY_SECONDS=2, EXTENDED_DELAY_SECONDS=30, EXTENDED_DELAY_INTERVAL=25. Audience row = programEnrollment + partner(email, users take:1). Ledger row = notificationEmail {id em_, type Bounty, emailId, bountyId, programId, partnerId, recipientUserId}.

### Decisive source
```ts
// gate ladder (route.ts :67-87) — relative bounties have no single announcement moment:
if (!bounty) return logAndRespond(`Bounty ${bountyId} not found.`, { logLevel: "error" });
if (bounty.startMode === BountyStartMode.relative)
  return logAndRespond(`Bounty ${bountyId} is relative-start; partner notifications skipped.`);
if (bounty.startsAt) {
  const diffMinutes = differenceInMinutes(bounty.startsAt, new Date());
  if (diffMinutes >= 10) return logAndRespond(`Bounty ${bountyId} not started yet, ...`);
}
// audience (:100-149) — empty groups/tags ⇒ ALL; portal-account requirement:
where: { programId, ...(groups && { groupId: { in: bountyGroupIds } }),
         ...(tags && { programPartnerTags: { some: { partnerTagId: { in: bountyPartnerTagIds } } } }),
         status: { in: ACTIVE_ENROLLMENT_STATUSES },
         partner: { email: { not: null }, users: { some: {} } } },   // signed up on partners.dub.co
take: EMAIL_BATCH_SIZE, skip: startingAfter ? 1 : 0, ...(startingAfter && { cursor: { id: startingAfter } }),
orderBy: { id: "asc" }
// send + ledger (:188-205) — per-batch idempotency key; ledger only on success:
{ idempotencyKey: `bounty-notify/${bountyId}-${startingAfter || "initial"}` }
if (data) await prisma.notificationEmail.createMany({ data: programEnrollments.map(({ partner }, idx) => ({
  id: createId({ prefix: "em_" }), type: NotificationEmailType.Bounty, emailId: data.data[idx].id, ... })) });
// requeue with delay ladder (:207-231):
if (programEnrollments.length === EMAIL_BATCH_SIZE) {
  let delay = 0;
  if (batchNumber > 0 && batchNumber % EXTENDED_DELAY_INTERVAL === 0) delay = EXTENDED_DELAY_SECONDS; // 30s every 25th
  else delay = BATCH_DELAY_SECONDS;                                                                  // else 2s
  await qstash.publishJSON({ url: `${APP_DOMAIN_WITH_NGROK}/api/cron/bounties/notify-partners`, method: "POST",
    delay, body: { bountyId, startingAfter, batchNumber: batchNumber + 1 } });
}
```
```ts
// publisher (bounties/route.ts :326-329 + :354-363) — schedule at creation, fire at startsAt:
const shouldSchedulePartnerNotifications = sendNotificationEmails && canSendEmailCampaigns
  && bounty.startMode !== BountyStartMode.relative;
qstash.publishJSON({ url: `.../api/cron/bounties/notify-partners`, body: { bountyId: bounty.id },
  ...(bounty.startsAt && { notBefore: Math.floor(bounty.startsAt.getTime() / 1000) }) });
```
**Flow:** bounty POST (business+ plan, pass-17 validation plane) schedules the campaign in the post-commit waitUntil fan-out with notBefore=startsAt → at fire time the cron verifies the QStash signature, re-runs the gate ladder (missing / relative / not-started all terminate with 200), then walks the audience in 100-row id-cursor batches (skip:1) → each batch goes through sendBatchEmail under its own Resend Idempotency-Key → on success the notificationEmail ledger rows are written (index-paired with the batch — safe because the query already filtered email-not-null) → full page self-requeues with a 2s delay, stretched to 30s on every 25th batch. From address derives from the program's first VERIFIED email domain (`<program.name> <bounties@<slug>>`), replyTo falls back to "noreply".
**Invariant:** (1) Terminal states answer 200 — a missing bounty or relative startMode must NOT make the queue retry; only real errors (signature, schema, DB) surface as non-2xx via handleAndReturnErrorResponse. (2) Idempotency is per-BATCH, keyed by the cursor position (`bounty-notify/<bountyId>-<startingAfter|initial>`): a redelivered batch is a no-op at the provider, while distinct batches never collide — retry safety and forward progress coexist. (3) The ledger is written ONLY when the provider returned data — a failed send leaves no phantom notification rows, and the index pairing between enrollments and provider ids depends on the query's email-not-null filter (drop that filter and idx alignment breaks). (4) The audience grammar (empty groups/tags ⇒ open to all) matches the visibility plane but is enforced SQL-only here — there is no second JS consumer to double-enforce against. (5) Provider politeness is structural: fixed 100-row batches, 2s inter-batch delay, 15× cooldown every 25th batch — the campaign paces itself regardless of audience size.
**Probe:** No direct test (grep tests/ for notify-partners = ∅). Deterministic probes executed at pin: constants :28-31; gate lines :68/:73/:82; audience filters :118/:121-127/:139-148; idempotencyKey :189; `if (data)` ledger gate :193; delay ladder :212-215; requeue body batchNumber+1 :225; publisher triple-conjunction :327-329 + notBefore floor(startsAt/1000) :361; NEGATIVE probe: no test file references this route, and no other cron publishes to it (single publisher at bounties/route.ts :356).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "notify-partners bounty email batch startingAfter idempotencyKey", limit: 10 }); // rank-1 expected: cron/bounties/notify-partners/route.ts
await mcp.codebase_memory.trace_path({ project: "dub", function_name: "sendBatchEmail", direction: "inbound", depth: 1 }); // expected: this cron + other campaign sites
```

## Verdict
Adopt the per-batch idempotency-key pattern (key = campaign-id + cursor-position) for any queue-walked bulk send: redelivery becomes a provider-side no-op while distinct batches stay distinct. Adopt 200-on-terminal-state for cron walkers whose inputs can legitimately vanish (deleted object, mode that skips the work) — the queue is for transient failures only. Adopt the success-gated ledger (write notification rows only after the provider acks, index-paired, with the query guaranteeing the pairing precondition). Adapt the delay ladder (base delay + periodic extended cooldown) to your provider's bulk limits. Omit nothing silently: a single campaign-wide idempotency key turns one redelivery into a silently truncated campaign; ledgering before the ack creates phantom notifications for emails that never went out.
