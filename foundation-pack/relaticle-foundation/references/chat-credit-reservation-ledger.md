<!-- capsule-v2 -->
# Credit reservation ledger — reserve up-front, settle-or-refund idempotently, drain allowance first

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you meter AI usage per team so concurrent requests, job retries, and crashes can neither double-charge nor leak credits?

## CreditService reserve/settle/refund over AiCreditTransaction ledger
**Path/Symbol:** `packages/Chat/src/Services/CreditService.php` (whole, 527L): `reserveCredit()` (:37-89), `settleReservation()` (:274-296), `settleReservedMinimum()` (:310-334), `recordResolution()` (:352-419), `purchasedAfter()` (:183-193), `addPurchasedCredits()` (:134-170).
**Signature:** `reserveCredit(Team $team, ?string $reservationKey = 'reserve-{turnId}', ...): bool`; all resolutions keyed `'resolve-{turnId}'`.
**Data Shape:** Ledger row: `(team_id, idempotency_key)` UNIQUE; types Reservation|Chat|Refund|Purchase. Balance row: credits_remaining, credits_used, purchased_credits with DB invariant `purchased_credits <= credits_remaining`.

### Decisive source
```php
$balance = AiCreditBalance::query()->where('team_id', $team->getKey())->lockForUpdate()->first();
if (! $balance instanceof AiCreditBalance || $balance->credits_remaining < 1) { return false; }
...
if ($reservationKey !== null) { AiCreditTransaction::query()->insertOrIgnore([... 'type' => Reservation ...]); }
```
Bucket-drain rule docblock (:177-182): "Spending drains the monthly allowance first... A refund has to reverse that: when every remaining credit was prepaid, the credit came out of the prepaid bucket and must go back there — otherwise it silently becomes an allowance credit that the next period reset wipes." Settlement writes ONE journal row (`insertOrIgnore` on the resolution key) whose insertion success gates the balance delta — duplicate/concurrent calls are silent no-ops.

**Flow:** dispatch-time reserve (journaled ⇒ retried jobs re-enter and get true without double-decrement) → stream completes: settleReservation charges `ceil(multiplier + toolCalls×bonus) − reserved` as a single adjusting delta → cancelled/failed/early-end: settleReservedMinimum keeps the reserved credit ('cancelled'|'job_failed') or refundReservation returns it — mutually exclusive by shared unique key → purchases arrive via Stripe-webhook-keyed insertOrIgnore then locked increment.
**Invariant:** Every mutation is (lock balance + unique-keyed journal insert) in one transaction; the prepaid bucket must be recomputed through `purchasedAfter()` on EVERY remaining-balance change, refunds included.
**Probe:** `tests/Feature/AI/CreditServiceTest.php`, `tests/Feature/Chat/CreditIdempotencyTest.php` (:17 no double-settle, :85 exactly-once, :109 settle-vs-refund mutual exclusion), `tests/Feature/Billing/CreditPackTest.php` (:39 allowance-first, :87 refunded-to-purchased).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "CreditService reserveCredit recordResolution settleReservation purchasedAfter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt journal-first metering: unique-keyed reservation rows + delta-applying settlement + bucket-aware refunds. Adapt pricing math and period reset to your billing. Omit Stripe checkout plumbing. Direct tests cover every idempotency polarity.
