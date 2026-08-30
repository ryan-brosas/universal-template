<!-- capsule-v2 -->
# Plan-sync downgrade ladder — when a Stripe subscription changes, when may the team's plan go DOWN, and why must billing side-effects never block lifecycle operations?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** A webhook says a subscription changed — how do you decide the team's resulting plan without letting an abandoned checkout, a trial, or an unrelated subscription ending strip a plan (or a sysadmin-assigned one) away?

## Grant-only-what-charged downgrade ladder
**Path/Symbol:** `app/Actions/Billing/SyncTeamPlanFromSubscription.php` (whole, 90L; `execute(Team $team, Subscription $subscription): void`, private `targetPlan(...): ?Plan`); entry point cited from `app/Listeners/Billing/SyncPlanOnStripeSubscriptionChange.php` (see `webhook-listener-fanout.md`); deletion-path twin `app/Actions/Billing/CancelTeamSubscription.php` (33L).
**Signature:** `Plan::fromStripePrice($subscription->stripe_price)` (config map `services.stripe.prices`, keys `<plan>_<interval>`) → null-unmapped → log + return (never guess a plan from an unknown price). Then `targetPlan`: `valid()` → subscription plan; else the ladder below. Plan change + `CreditService::resetPeriod($team)` run in ONE `DB::transaction`.
**Data Shape:** `NON_GRANTING_STATUSES = ['incomplete', 'incomplete_expired']` — Stripe statuses a subscription holds without ever having granted access.

### Decisive source
```php
// A subscription that never charged (abandoned or failed checkout) has
// granted nothing, so it must not take anything away either.
if (in_array($subscription->stripe_status, self::NON_GRANTING_STATUSES, true)) {
    return null;
}

// A running trial grants the same plan a subscription would, so plan
// equality alone cannot prove this subscription is what granted it.
if ($team->onGenericTrial()) {
    return null;
}

// Only downgrade a plan this subscription granted — a sysadmin-assigned
// plan (e.g. Enterprise) must survive an unrelated subscription ending.
if ($team->plan === $subscriptionPlan) {
    return Plan::default();
}

return null;
```

**Flow:** webhook (post-Cashier) → price→plan map (unmapped = log + stop) → validity check → non-granting statuses stop (never downgrade for a checkout that never charged) → trial ambiguity stops → downgrade only when the current plan is exactly the plan THIS subscription granted → transactional plan save + credit-period reset. The deletion twin `CancelTeamSubscription` is log-never-throw: no subscription or already-`ended()` → silent return; the Cashier `cancel()`/`cancelNow()` call is wrapped in try/catch → `Log::error` — a Stripe outage must not block team deletion.
**Invariant:** Downgrades require proven grant provenance: this subscription's plan must equal the team's current plan, and neither a trial nor a never-charged checkout may trigger one. Unmapped prices are logged, never guessed. Billing API failures must degrade to logs, never abort the surrounding lifecycle operation (deletion, webhook handling).
**Probe:** `tests/Feature/Billing/TeamDeletionBillingTest.php` — no-subscription no-op, already-ended no-op, unreachable-Stripe logs and leaves `stripe_status` active (`->throwsNoExceptions()` on all three). The downgrade ladder itself is pinned by the webhook-listener tests cited in `webhook-listener-fanout.md`.

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "SyncTeamPlanFromSubscription targetPlan NON_GRANTING_STATUSES onGenericTrial CancelTeamSubscription resetPeriod fromStripePrice", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the provenance-gated downgrade ladder: map price→plan explicitly, refuse to downgrade on non-granting statuses or trial ambiguity, and only ever downgrade a plan the same subscription granted (external plan assignments survive unrelated subscription endings). Adopt log-never-throw for billing calls inside lifecycle operations. Adapt the Stripe/Cashier specifics and the plan enum; keep the reset-credits-with-plan-change transactional pairing. Companion to `webhook-listener-fanout.md` (the listener that feeds this action) and `credit-seeding-billing-period.md` (what `resetPeriod` acts on).
