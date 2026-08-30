<!-- capsule-v2 -->
# Billing UI server-side action gates — a Livewire page method is reachable even when the button that renders it is not, so which gates must re-run server-side?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** A billing page renders buttons conditionally (owner-only, feature-flagged, eligibility-gated) — which of those conditions must be re-enforced inside each Livewire action, and how do checkout failures degrade?

## Page actions with per-method re-gating
**Path/Symbol:** `app/Filament/Pages/Billing.php` (`mount` :54, `startTrial` :59, `upgrade` :86, `managePortal` :102, `buyCredits` :118, `notifyCheckoutFailed` :134, `getViewData` :143, `trialAvailable` :171; 191L).
**Signature:** `startTrial(StartProTrial $startProTrial): void`; `upgrade(CreateProCheckout $createCheckout, string $interval = 'monthly'): void`; `buyCredits(CreateCreditPackCheckout $createCheckout, string $pack): void`; `trialAvailable(): bool`.
**Data Shape:** `#[Url]` public props `?string $checkout` and `?string $credits` carry the return-URL state (`checkout=success` → `activating` banner until the subscription actually exists; `credits=success` → `creditsFulfilling` pending-fulfillment notice). View data reads `HostedWorkspaceAccess::allows($team)` and `hosted_free_grandfathered_at` directly.

### Decisive source
```php
public function startTrial(StartProTrial $startProTrial): void
{
    // The button is only rendered for an eligible workspace, but the
    // Livewire method is reachable regardless — enforce it server-side.
    if (! $this->trialAvailable()) {
        Notification::make()->title(__('billing.trial.not_available'))->danger()->send();

        return;
    }
```
```php
public function upgrade(CreateProCheckout $createCheckout, string $interval = 'monthly'): void
{
    $team = $this->team();

    if (! $this->user()->ownsTeam($team) || $team->subscribed()) {
        return;
    }

    try {
        $this->redirect($createCheckout->execute($team, $interval));
    } catch (Throwable $exception) {
        report($exception);
        $this->notifyCheckoutFailed();
    }
}
```

**Flow:** `mount()` hard-gates the whole page on the Billing Pennant feature (403 when off). Every mutating action then re-checks its own preconditions server-side: `startTrial` re-runs `trialAvailable()` (Free plan AND `pro_trial_used_at === null` AND no subscriptions row — the escape hatch for grandfathered workspaces that never received the automatic creation-time trial) and turns an `AuthorizationException` from the action into a danger notification; `upgrade` and `buyCredits` re-check `ownsTeam` (buyCredits additionally re-runs `HostedWorkspaceAccess::allows` — a paused workspace gets a silent no-op, not a checkout); `managePortal` re-checks ownership only. All three Stripe-touching actions wrap the call in `catch (Throwable)` → `report($exception)` + a friendly notification, so a missing Stripe secret degrades to "checkout failed", never a 500. Members get a read-only view (`getViewData` computes `isOwner` and the blade hides actions).
**Invariant:** Rendering a button is never the gate. Each Livewire method is independently reachable (Livewire public methods are callable by crafted requests), so every precondition the blade used to decide visibility must be re-evaluated inside the method — and a business refusal degrades to a notification, while an infrastructure failure is reported to error tracking and ALSO degrades to a notification.
**Probe:** `tests/Feature/Billing/BillingPageTest.php` (22 cases: `assertForbidden` with feature off; "refuses a second trial on a workspace even when called directly" pins the server-side re-gate of a hidden button; "blocks the trial action for non-owners"; "shows a graceful error instead of 500 when checkout cannot start"; `buyCredits` refused for paused workspace and non-owner with `assertNoRedirect` + `assertNotNotified`; meter denominator = plan allowance, not remaining+used).

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "Billing page startTrial upgrade buyCredits trialAvailable notifyCheckoutFailed getViewData", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the discipline: feature-flag the page at mount, re-check every visibility precondition inside each public action, treat business refusals as notifications and infrastructure failures as report+notification, and carry checkout-return state as URL params that render pending-state banners. Adapt the Livewire/Filament page mechanics, Pennant feature resolution, and Cashier subscription checks to your UI stack. Companion: `consent-stamped-workspace-access.md` (the HostedWorkspaceAccess ladder buyCredits re-runs).
