<!-- capsule-v2 -->
# Batch email queue — how do you send N templated emails idempotently through a queue, and where do QStash and Resend dedup keys have to agree?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What is the chunk/idempotency contract of queueBatchEmail that callers like the payout router rely on?

## queueBatchEmail: filter → 100-chunk → per-batch derived keys
**Path/Symbol:** `apps/web/lib/email/queue-batch-email.ts:queueBatchEmail` (:18-70); queue singleton (:14-16); consumer route `apps/web/app/(ee)/api/cron/send-batch-email/`.
**Signature:** `queueBatchEmail<TTemplate>({to,subject,variant,templateName,templateProps,...}[], {idempotencyKey?}): Promise<string[]>`.
**Data Shape:** BATCH_SIZE=100; named QStash queue `send-batch-email`; key derivation `idempotencyKey` for single batch, `${idempotencyKey}-batch-${i}` when multiple.

### Decisive source
```ts
emails = emails.filter((email) => Boolean(email.to));
if (emails.length === 0) return [];
const batches = chunk(emails, BATCH_SIZE);
const idempotencyKey = options?.idempotencyKey
  ? batches.length > 1 ? `${options.idempotencyKey}-batch-${i}` : options.idempotencyKey
  : undefined;
const response = await queue.enqueueJSON({
  url: `.../api/cron/send-batch-email`, body: batch,
  ...(idempotencyKey && { deduplicationId: idempotencyKey }),        // QStash dedup
  ...(idempotencyKey && { headers: { "Idempotency-Key": idempotencyKey } }) }); // Resend dedup
```
(:24-58)

**Flow:** drop recipients without an address (never throw) → chunk → enqueue each chunk through a NAMED queue (serialized ordering) with BOTH dedup mechanisms keyed identically → return collected messageIds; failures log to Slack-mention channel then rethrow so callers can distinguish "queued" from "not queued".
**Invariant:** (1) the SAME string must be QStash's deduplicationId AND Resend's Idempotency-Key — covering only one layer still double-sends on redelivery at the other; (2) multi-batch suffixing means a caller whose list size crosses a 100-boundary between retries gets NEW keys for shifted batches — pass a stable caller-scoped base key and accept at-least-once semantics beyond that; (3) empty input is a successful no-op ([]), matching the allSettled style of every payout fan-out.
**Probe:** deterministic probe: `grep -n 'deduplicationId: idempotencyKey' apps/web/lib/email/queue-batch-email.ts | head -1` = :51; `grep -c 'chunk(emails, BATCH_SIZE)' apps/web/lib/email/queue-batch-email.ts` = 1. No upstream unit suite covers this file directly (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "queueBatchEmail", limit: 5 });
```

## Verdict
Adopt dual-layer idempotent batch email enqueue as-is. Adapt template registry and providers. Omit nothing else — this capsule plus cron-dual-auth covers the whole helper.
