<!-- capsule-v2 -->
# CreditService reservation ledger — how does a prepaid credit survive reserve→settle→refund across queue retries without ever double-charging?

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** what makes every credit mutation idempotent, mutually exclusive per turn, and orphan-recoverable?

## insertOrIgnore on (team_id, idempotency_key) as the single commit point
**Path/Symbol:** `packages/Chat/src/Services/CreditService.php` (`reserveCredit` :37-89, `recordResolution` :352-419, `settleReservation` :274-303, `refundReservation` :96-112, `settleReservedMinimum` :310-332, `purchasedAfter` :183-193).
**Signature:** `reserveCredit(Team, ?string $reservationKey = 'reserve-{turnId}', ?string $conversationId, ?string $userId): bool`; `recordResolution(...): bool`.
**Data Shape:** `ai_credit_balances(team_id PK, credits_remaining, credits_used, purchased_credits, period_*)` + append-only `ai_credit_transactions(id ULID, team_id, idempotency_key UNIQUE-with-team, type ∈ Reservation|Chat|Refund|Purchase|Adjustment, credits_charged, metadata)`.

### Decisive source
```php
$inserted = AiCreditTransaction::query()->insertOrIgnore([
    ... 'idempotency_key' => $resolutionKey, 'type' => $type->value, ...
]);
if ($inserted === 0) {
    return false;                    // someone already resolved this key: silent no-op
}
// only the winner touches the balance:
$newRemaining = max($balance->credits_remaining + $remainingDelta, 0);
$balance->update(['credits_remaining' => $newRemaining,
                  'credits_used' => max($balance->credits_used + $usedDelta, 0),
                  'purchased_credits' => $this->purchasedAfter($balance, $newRemaining)]);
```
Refund-vs-settle exclusivity is structural: both write "the same unique key", so whichever lands first wins and the other becomes `inserted === 0`. The prepaid bucket rule:
```php
// Spending drains the monthly allowance first ... A refund has to reverse that: when
// every remaining credit was prepaid, the credit came out of the prepaid bucket and
// must go back there — otherwise it silently becomes an allowance credit that the
// next period reset wipes.
private function purchasedAfter(AiCreditBalance $balance, int $newRemaining): int
```

**Flow:** send → `reserveCredit` inside tx: key-exists check → `lockForUpdate` balance row → refuse when <1 credit → decrement, write Reservation ledger row (`insertOrIgnore`) → stream runs. Outcome paths ALL funnel into `recordResolution`: settle (charge real cost minus reserved), settle-minimum (cancel/timeout/failure keep the reserved unit), refund (pre-model death). An orphan sweeper refunds reservations older than a window whose keys never resolved; a late settle after such refund is a no-op because the sweeper consumed the key. Period reset re-grants allowance + surviving purchased credits and journals an Adjustment row.
**Invariant:** at most one ledger row per (team, resolutionKey) — the unique index converts every race into an ordered no-op; balance mutations happen only in the transaction that won the key; `credits_used` moves in lockstep with chat-type ledger rows; purchased_credits ≤ credits_remaining enforced via `purchasedAfter` on EVERY path.
**Probe:** `tests/Feature/Chat/CreditIdempotencyTest.php` (:17 double settle charges once, :51 duplicate-key rejection at DB level, :85 reservation settled once, :109 settle/refund mutual exclusion); `CreditReservationLedgerTest.php` (:15 reserve-once, :33 ledger row shape, :62 orphan refund window, :85 settled rows never refunded, :117 late settle after sweep = no-op, :166 broke team refused); `CreditsUsedInvariantTest.php` (:57 cycle lockstep); `RefundReservationLedgerTest.php`, `ProcessChatMessageSettlementTest.php`.
**Coverage caveat:** none beyond standard best-effort.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "CreditService reserveCredit recordResolution purchasedAfter", limit: 8, fields: ["signature", "lines"] });
```

## Verdict
Adopt: journal-first metering for any billable async unit — reserve under lock with a journaled idempotency key, resolve outcomes through one insertOrIgnore chokepoint, add an orphan sweeper for keys that never resolve. Adapt pricing/multiplier logic. Omit Stripe purchase plumbing and plan-reset specifics.
