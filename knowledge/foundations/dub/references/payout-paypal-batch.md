<!-- capsule-v2 -->
# PayPal batch payout — how do you pay N partners over PayPal with a cached OAuth token, and what does the status machine look like across sent/failed/completed?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** How is the PayPal access token kept fresh without a request-time OAuth round-trip on every batch, and which statuses may a partner retry?

## token cache + batch sender + partner retry action
**Path/Symbol:** `apps/web/lib/paypal/create-paypal-token.ts:createPaypalToken` (:13-57); `apps/web/lib/paypal/create-batch-payout.ts:createPayPalBatchPayout` (:12-49); retry `apps/web/lib/actions/partners/retry-failed-paypal-payouts.ts` (:29-118); invoice driver `apps/web/app/(ee)/api/cron/payouts/charge-succeeded/send-paypal-payouts.ts:sendPaypalPayouts` (:11-91); sandbox switch `apps/web/lib/paypal/env.ts:1-10`.
**Signature:** `createPaypalToken(): Promise<string>`; `createPayPalBatchPayout({ payouts: [{id,amount,partner:{paypalEmail},program:{name}}], invoiceId })`.
**Data Shape:** body `{sender_batch_header:{sender_batch_id:invoiceId}, items:[{recipient_type:"EMAIL", receiver, sender_item_id:payout.id, note, amount:{value:(cents/100).toString(), currency:"USD"}}]}`.

### Decisive source
```ts
const cachedToken = await redis.get(TOKEN_CACHE_KEY);        // "paypal:token"
if (cachedToken) return cachedToken;
...
waitUntil(redis.set(TOKEN_CACHE_KEY, token.access_token, {
  ex: token.expires_in - 60 * 5,   // 5 min buffer
}));
```
(create-paypal-token.ts :19-53)
```ts
const updateResult = await tx.payout.updateMany({
  where: { id: payout.id, status: "failed" },     // re-check INSIDE the claim
  data: { status: "processing" } });
if (updateResult.count === 0)
  throw new Error("This payout is already being processed or has been sent...");
```
(retry-failed-paypal-payouts.ts :76-84)

**Flow:** token: Redis-cached client-credentials grant with a 5-minute expiry buffer, written via waitUntil so the caller never blocks; batch: one POST per invoice keyed by `sender_batch_id = invoiceId` (PayPal dedups on it) → driver marks payouts `sent` immediately after 2xx + fires allSettled(batch emails, referral queue) → failures land via the `payout-failed` webhook route (`stripePayoutId`-keyed updateMany to `failed`+failureReason :46-55 of that route) → partner retries through an action gated by `ratelimit(1,"12 h")` per payoutId and a transactional failed→processing claim; batch creation failure REVERTS processing→failed so it stays retryable (:96-112); success appends `-nanoid(7)` to the invoice id so PayPal sees a NEW batch id (:87-90). Completion arrives at `payout-paid` (`status:"completed"` + traceId :50-53).
**Invariant:** (1) token TTL is expires_in minus buffer — storing the raw value risks serving an expired token near the boundary; single shared cache key is safe because tokens are account-scoped; (2) only `failed` payouts are retryable and the flip is a guarded count-checked UPDATE, so concurrent retries cannot double-pay even before PayPal's own batch-id dedup; (3) cents→dollars conversion happens at the LAST step as string, never floating math on the stored integer.
**Probe:** deterministic probe: `grep -n 'ex: token.expires_in - 60 \* 5' apps/web/lib/paypal/create-paypal-token.ts` = :51; `grep -c 'ratelimit(1, "12 h")' apps/web/lib/actions/partners/retry-failed-paypal-payouts.ts` = 1. No upstream unit suite (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "createPayPalBatchPayout", limit: 5 });
```

## Verdict
Adopt the buffered-token Redis cache, invoice-keyed batch id, and failed-only guarded retry ladder. Adapt endpoint hosts/sandbox switching and email fan-out. Omit PayPal's webhook verification plane (PAYPAL_WEBHOOK_ID exists but no receiver was mined) unless your port consumes PayPal callbacks.
