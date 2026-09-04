<!-- capsule-v2 -->
# Orphan reservation sweeper — refund via the resolution key so a late settle is a silent no-op

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** How do you release credit holds from turns that died between reserve and settle without ever double-applying refund and settlement?

## Key-rewrite anti-join + idempotent refund
**Path/Symbol:** `packages/Chat/src/Commands/ReleaseOrphanedReservationsCommand.php` (whole, 68L, signature `chat:release-orphaned-reservations {--age=30}`); proposal-side twin `Commands/ExpirePendingActionsCommand.php` → `PendingActionService::expireStale()` (:418-426) over the `#[Scope] expired()` scope (`Models/PendingAction.php` :104-110).
**Signature:** orphan predicate: `type = Reservation AND created_at < now()-age AND idempotency_key LIKE 'reserve-%' AND NOT EXISTS (resolved row with key = replace(key,'reserve-','resolve-'))`.
**Data Shape:** `ai_credit_transactions.idempotency_key` carries the turn's phase prefix (`reserve-…` / `resolve-…`); unique `(team_id, idempotency_key)` index makes any duplicate phase write a no-op; `--age` floored at 5 minutes; 500-row batch limit per run.

### Decisive source
```php
/**
 * Refund credit reservations whose turn died between reserve and settle
 * (worker crash, deploy kill, lost job). The refund uses the turn's RESOLUTION
 * key, so if the original job somehow settles later the unique
 * (team_id, idempotency_key) index makes that settle a silent no-op — refund
 * and settle can never both apply.
 */
$orphans = AiCreditTransaction::query()
    ->where('type', AiCreditType::Reservation->value)
    ->where('created_at', '<', now()->subMinutes($age))
    ->where('idempotency_key', 'like', 'reserve-%')
    ->whereNotExists(function (Builder $query): void {
        $query->selectRaw('1')->from('ai_credit_transactions as resolved')
            ->whereColumn('resolved.team_id', 'ai_credit_transactions.team_id')
            ->whereRaw("resolved.idempotency_key = replace(ai_credit_transactions.idempotency_key, 'reserve-', 'resolve-')");
    })->oldest()->limit(500)->get();
```
The twin sweeper closes the proposal lifecycle the same way: `expireStale()` bulk-updates every row matched by `expired()` (= status Pending AND `expires_at < now()`, expiry stamped from `chat.pending_action_expiry_minutes`=15) to Expired with `resolved_at`.

**Flow:** scheduler runs the command → anti-join selects unsettled reservations past the age floor → for each, look up the team (skip if the team vanished) → `CreditService::refundReservation(resolutionKey: 'resolve-'+same-suffix, …)` writes the REFUND under the SAME idempotency key a real settle would use → if the "dead" job later wakes and settles, the unique index swallows it. Missing team rows are skipped in place, never aborting the sweep.
**Invariant:** One idempotency-key namespace per turn across BOTH directions of the ledger — recovery reuses the forward path's key instead of minting its own, which is what makes refund-then-settle impossible rather than merely unlikely. Sweeps are bounded (500) and age-floored so a slow-but-alive worker is never mistaken for an orphan.
**Probe:** `tests/Feature/Chat/CreditReservationLedgerTest.php` — refunds orphans older than the window and asserts a `Refund` transaction exists at `resolve-orphan-1` (:62-83), settled reservations are untouched (:85-115), and a settle arriving AFTER the sweeper refunded is a no-op keeping the balance stable (:117+).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "release-orphaned-reservations expireStale idempotency_key reserve resolve refundReservation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt key-rewrite recovery whenever a two-phase ledger can lose its worker between phases. Adapt table/column names to your schema; keep the unique-index pairing as the correctness anchor, not application-level checks. Omit Reverb/console presentation. Companion to `credit-reservation-ledger.md`, which defines the reserve/settle keys this sweeper reuses.
