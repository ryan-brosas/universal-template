<!-- capsule-v2 -->
# Idempotent credit seeding — lockForUpdate early-return plus a convergence-loop billing period

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** How do you seed a per-team credit allowance exactly once at team creation, with a billing period that survives month-end anniversary anchors?

## Seed-once balance with audit trail
**Path/Symbol:** `app/Actions/Chat/SeedTeamCreditBalance.php` (whole, 67L, `public function execute(Team $team): AiCreditBalance`); invoked by `app/Listeners/SeedTeamCreditBalanceListener.php` on Jetstream `TeamCreated`; period source `packages/Chat/src/Services/CreditPeriodResolver.php` (89L, `boundsFor(Team $team): array{start: Carbon, end: Carbon}`).
**Signature:** `DB::transaction` → `AiCreditBalance::where('team_id')->lockForUpdate()->first()` → early return if present → `create([credits_remaining => $plan->credits(), period_starts_at/ends_at => $this->periods->boundsFor($team)])` → audit `AiCreditTransaction` with `idempotency_key = 'seed-initial-'.Str::ulid()` and `metadata = [action: 'seed_initial_balance', plan, allowance_granted]`.
**Data Shape:** `Plan::credits()` ladder: Free 300 / Pro 2,000 / Enterprise 10,000 (`app/Enums/Plan.php` :49-58). The unique `(team_id, idempotency_key)` index on `ai_credit_transactions` (same ledger as the reservation sweeper capsule) makes duplicate audit writes no-ops.

### Decisive source
```php
$existing = AiCreditBalance::query()
    ->where('team_id', $team->getKey())
    ->lockForUpdate()
    ->first();
if ($existing instanceof AiCreditBalance) {
    return $existing;
}
```
**Period policy ladder (CreditPeriodResolver::boundsFor):** valid subscription → anniversary cycle from `subscription.created_at`; else generic trial → `[trial_ends_at - StartProTrial::TRIAL_DAYS(14), trial_ends_at]`; else calendar month `[now()->startOfMonth(), now()->endOfMonth()]`. The anniversary cycle is recomputed from the anchor EVERY call (never chained) so month-end anchors clamp without drifting (Jan 31 → Feb 28 → Mar 31):
```php
$elapsed = max(0, (int) $anchor->diffInMonths($now));
for ($i = 0; $i <= self::MAX_CYCLE_ADJUSTMENTS; $i++) {
    $start = $anchor->copy()->addMonthsNoOverflow($elapsed);
    $end = $anchor->copy()->addMonthsNoOverflow($elapsed + 1);
    if ($start->lessThanOrEqualTo($now) && $now->lessThan($end)) {
        return ['start' => $start, 'end' => $end];
    }
    $elapsed = max(0, $elapsed + ($start->greaterThan($now) ? -1 : 1));
}
throw new RuntimeException('CreditPeriodResolver failed to converge …');
```
`diffInMonths()` only seeds the guess: it uses overflow-style month arithmetic and disagrees with `addMonthsNoOverflow()` by up to a month near month-end anchors, so the loop walks `$elapsed` toward whichever direction `start <= now < end` fails, bounded by `MAX_CYCLE_ADJUSTMENTS = 6`, and exhausting the cap throws rather than silently returning a past window (which would make the nightly `chat:reset-credits` re-grant a full allowance).

**Flow:** team created → listener → seed action → locked read decides create-vs-return → balance + audit row written in one transaction with the plan's allowance and resolved period bounds → later reseeds (or a concurrent second listener) return the existing row.
**Invariant:** Idempotency is structural (locked early-return), not a flag; the audit transaction records plan and allowance for support forensics. Period windows must always contain `now()` or the run fails loudly — a silently stale window converts a monthly grant into a nightly one.
**Probe:** `tests/Feature/Chat/SeedTeamCreditBalanceTest.php` — double-seed returns the same key with count 1 and exactly one `seed_initial_balance` audit; Pro/Enterprise allowances; trial team pins `period_ends_at = trial_ends_at` and `period_starts_at = trial_ends_at - 14d`. `tests/Feature/Chat/TeamCreatedSeedsBalanceTest.php` pins the listener fires on both normal and signup personal-team flows.

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "SeedTeamCreditBalance boundsFor anniversaryCycle addMonthsNoOverflow lockForUpdate seed-initial", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the locked-early-return seed for any per-tenant provisioned resource, and the anchor-recompute convergence loop for anniversary billing periods whenever month-end anchors exist. Adapt plan values and key prefixes; keep the fail-loud convergence cap — it is the difference between a bug and an outage. Omit the trial-span branch if you have no trials. Companion to `credit-reservation-ledger.md` (same transaction table) and `orphan-reservation-sweeper.md` (same idempotency-key namespace).
