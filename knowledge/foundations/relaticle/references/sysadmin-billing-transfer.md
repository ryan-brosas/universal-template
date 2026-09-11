<!-- capsule-v2 -->
# Stripe-customer workspace transfer — how do you move paid billing between two owned workspaces without touching the subscription in Stripe?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** A sysadmin must move a Stripe customer and all its subscriptions from workspace A to workspace B (same owner). What moves, what never leaves your DB, and what guards the pair?

## TransferWorkspaceBilling: customer handover, zero subscription writes
**Path/Symbol:** `packages/SystemAdmin/src/Actions/TransferWorkspaceBilling.php` :32 `execute(Team $source, Team $target, string $sysadminId)`, :104 `assertTransferable()`.
**Signature:** `execute(): void` — throws `TransferRefused` on every precondition failure; `readonly` service, `CreditService` injected.
**Data Shape:** Team carries denormalized billing columns: `stripe_id` (customer), `pm_type`, `pm_last_four`, `plan` (enum), `trial_ends_at`. Subscriptions table has `team_id` but NO team column in Stripe itself — items follow their parent subscription row.

### Decisive source
```php
$plan = $this->assertTransferable($lockedSource, $lockedTarget);
...
$lockedSource->forceFill(['stripe_id' => null, 'pm_type' => null, 'pm_last_four' => null,
    'plan' => $lockedSource->plan === $plan ? Plan::default() : $lockedSource->plan,
    'trial_ends_at' => null])->save();
$lockedTarget->forceFill(['stripe_id' => $sourceStripeId, ... ])->save();
Subscription::query()->where('team_id', $lockedSource->getKey())
    ->update(['team_id' => $lockedTarget->getKey()]);
```
(:34-65, inside one `DB::transaction` with BOTH teams re-fetched `lockForUpdate()` by key). Docblock states the core insight: "The subscription itself is never sent to Stripe. It cannot change customer there, and it does not need to: the customer itself changes hands, so the same card keeps being charged on the same date."

**Flow:** lock both rows → assertTransferable (same-team / no-source-customer / target-has-customer / different-owner / target-scheduled-for-deletion / no-valid-subscription / unmapped-price all refuse) → clear source billing cols BEFORE populating target so the two rows never briefly share a stripe_id → plan mirror: source drops to default ONLY if its plan was the one the subscription granted (a sysadmin-assigned Enterprise survives) → bulk-move EVERY subscription row (`subscription_items` follow the parent) → unsetRelation('subscriptions') on both because CreditPeriodResolver reads the relation and loadMissing would keep the pre-move copy → credit periods reset for both INSIDE the tx → after commit: rename the Stripe customer to the target workspace, swallowing failure (money already moved correctly; an outage must not undo or misreport it).
**Invariant:** Exactly one Stripe write exists (the cosmetic rename), post-commit and failure-tolerant; precondition failures use a NARROW exception type — catching bare RuntimeException swallowed infrastructure failures (ModelNotFound/QueryException are RuntimeException subtypes) and reported them as business refusals instead of letting them reach error tracking.
**Probe:** `tests/Feature/SystemAdmin/SubscriptionTransferActionTest.php` (:101 happy path asserts every moved column + specific notification; :126 second-subscription bulk-move contract; :148 Enterprise-plan preservation; :163 Pro allowance + purchased credits survive; :185 target period anchored on ORIGINAL subscription created_at while :203 source falls back to calendar month; :236/:302/:315 direct-call guard tests bypassing Filament's option-list validation; :390 exactly ONE Stripe call `/v1/customers/{id}` with `['name'=>…]`; :407 committed transfer survives rename failure).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "TransferWorkspaceBilling execute assertTransferable TransferRefused", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt customer-handover-over-subscription-rewrite for intra-owner billing moves plus the narrow-refusal-exception + UI-halt pairing; adapt column names/credit plumbing; omit Relaticle's Filament resource specifics. 20 direct tests pin guards, ordering, and the single-write boundary.
