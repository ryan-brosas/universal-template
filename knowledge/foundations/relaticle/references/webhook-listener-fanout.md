<!-- capsule-v2 -->
# Webhook + ESP listener fan-out — silent early-returns, release-not-drop retries, afterCommit dispatch

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** How should event listeners that bridge to external systems (Stripe webhooks, an email marketing platform) fail — and how do they avoid emitting for transactions that never committed?

## Prefix-filtered webhook sync with silent mismatches
**Path/Symbol:** `app/Listeners/Billing/SyncPlanOnStripeSubscriptionChange.php` (whole, 44L, `handle(WebhookHandled $event): void`); delegates to `app/Actions/Billing/SyncTeamPlanFromSubscription.php` (`execute(Team $team, Subscription $subscription): void`, constructor-injected `CreditService`).
**Signature:** `str_starts_with((string) ($event->payload['type'] ?? ''), 'customer.subscription.')` → `Subscription::query()->firstWhere('stripe_id', $stripeId)` → `$subscription->owner()->first()` → `$this->syncTeamPlan->execute($team, $subscription)`; every resolution step returns silently on mismatch (wrong prefix, non-string id, unknown subscription, non-Team owner).
**Data Shape:** listens to Laravel Cashier's `WebhookHandled` (fired AFTER Cashier processed the webhook, so local subscription rows are already synced) — not the raw `WebhookReceived`.

### Decisive source
```php
$type = $event->payload['type'] ?? '';

if (! str_starts_with((string) $type, 'customer.subscription.')) {
    return;
}
...
$subscription = Subscription::query()->firstWhere('stripe_id', $stripeId);

if (! $subscription instanceof Subscription) {
    return;
}
```

## ESP tag listeners: release-not-drop + afterCommit
**Path/Symbol:** `app/Listeners/Email/TeamCreatedTagListener.php` (61L, queued, `#[Backoff(15)] #[Tries(10)]`), `app/Listeners/Email/TeamMemberAddedListener.php` (38L), `app/Listeners/Email/NewSubscriberListener.php` (67L, on `Verified`), `app/Listeners/Email/RecordLoginTimestampListener.php` (26L, on `Login`).
**Signature:** all ESP listeners gate on `config('mailcoach-sdk.enabled_subscribers_sync', false)` first. The queued tag listener: owner without `mailcoach_subscriber_uuid` (async ESP provisioning) → `$this->release(15)` — retry later instead of dropping; jobs dispatched `->afterCommit()`.

### Decisive source
```php
if (! $owner->mailcoach_subscriber_uuid) {
    $this->release(15);

    return;
}

dispatch(new ModifySubscriberTagsJob(
    $owner->mailcoach_subscriber_uuid,
    $tags,
    TagAction::Add,
))->afterCommit();
```
`RecordLoginTimestampListener` writes `last_login_at` with `saveQuietly()` (no activity-log churn) and skips same-day re-logins (`$user->last_login_at->isToday()` early return) — one write per user-day. `NewSubscriberListener` assembles the subscriber payload (Verified tag + signup-source social/organic + onboarding tags) and dispatches `SyncSubscriberJob` afterCommit.

**Flow:** provider event → config gate → cheap prefix/type filter → local-entity resolution with silent early-returns → action execution (or queued job after commit); missing external dependency (uuid) ⇒ release with backoff, never drop.
**Invariant:** A webhook or event for an entity this installation doesn't know must never throw (webhook handlers are re-entry points for attacker-controlled payloads). Work that references rows created in the same transaction must be dispatched afterCommit, or the job can read a row that gets rolled back. A not-yet-provisioned external id is a retry condition, not a failure.
**Probe:** `tests/Feature/Email/TeamCreatedTagListenerTest.php` — tag payload shape (`['use-case:sales', 'referral:google']`), only-use-case variant, uuid-missing release. `tests/Feature/Email/TeamMemberAddedListenerTest.php`, `tests/Feature/Email/NewSubscriberListenerTest.php`, `tests/Feature/Email/RecordLoginTimestampTest.php` (same-day re-login writes nothing).

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "SyncPlanOnStripeSubscriptionChange WebhookHandled customer.subscription TeamCreatedTagListener release afterCommit mailcoach_subscriber_uuid", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the silent-early-return ladder for any inbound webhook listener (prefix filter → id lookup → owner resolution, each a quiet return) and the release-with-backoff pattern for listeners awaiting an asynchronously provisioned external id. Adopt afterCommit dispatch for any job touching rows created in the firing transaction. Adapt the ESP (Mailcoach) and Cashier specifics; keep the single config kill-switch per integration. Omit the subscriber-tag taxonomy (product surface). Companion to `sysadmin-billing-transfer.md` (the plan-sync action's sibling) and `team-bootstrap-listeners.md` (the same TeamCreated event, sync side).
