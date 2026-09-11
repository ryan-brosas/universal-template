<!-- capsule-v2 -->
# Credit-pack admission ladder — how do configured prices, paid sessions, and customer binding prevent premature prepaid-credit grants?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5dcc97765fcba6fdf62585c541e1b`; direct source/test read (Codebase Memory MCP unavailable this session). **Question:** Which independent gates must a Stripe credit-pack webhook pass before it may reach the idempotent credit ledger?

## Catalog, payment-state, metadata, and customer gates compose before fulfillment
**Path/Symbol:** `app/Services/Billing/CreditPackCatalog.php:purchasable/find/creditsForPrice` (:15-61); `app/Http/Controllers/Billing/StripeWebhookController.php:handleCheckoutSessionCompleted/handleCheckoutSessionAsyncPaymentSucceeded/fulfillCreditPackCheckout` (:58-145); `app/Actions/Billing/GrantPurchasedCredits.php:execute` (:20-40).
**Signature:** `purchasable(): array<string,array{price:string,credits:int}>`; `creditsForPrice(string): ?int`; `fulfillCreditPackCheckout(array): Response`; `execute(Team,string,string): bool`.
**Data Shape:** Config entries are accepted only when `price` is a non-empty string and `credits` is a positive integer. A payment session must have `mode=payment`, a paid status (the synchronous handler requires `payment_status=paid`), string metadata `team_id`/`credit_pack_price`, a string session id, and a customer matching the team's `stripe_id`. The action maps the configured price to an integer and passes `pack-{sessionId}` to `CreditService::addPurchasedCredits`; unknown prices return false after a warning.

### Decisive source
```php
if (($session['payment_status'] ?? null) !== 'paid') {
    return $this->successMethod();
}

if (($session['mode'] ?? null) !== 'payment') {
    return $this->successMethod();
}
```
```php
if (! $team instanceof Team || ! is_string($customerId) || $team->stripe_id !== $customerId) {
    Log::warning('Credit pack checkout ignored: team/customer mismatch', [...]);
    return $this->successMethod();
}

$this->grantCredits->execute($team, $priceId, $sessionId);
```

**Flow:** `CreditPackCatalog` filters malformed or unpriced config before it can be displayed or resolved. The synchronous checkout handler declines unpaid sessions; the asynchronous-success handler handles delayed payment confirmation. Both call a shared method that declines subscription-mode sessions, malformed metadata, and team/customer mismatches with a successful webhook response (no retry storm). `GrantPurchasedCredits` declines an unknown configured price and logs. For an admitted price, `CreditService` inserts a purchase ledger row and updates the balance in one transaction, keyed by the checkout session id; replay therefore becomes a no-op.
**Invariant:** No credits are granted merely because a checkout event exists. Money must be paid (or asynchronously confirmed), the event must be a one-time payment session, metadata must resolve a real team, and the Stripe customer must be that team's customer. Every rejection acknowledges the webhook without mutating credit state; every accepted session is idempotent at the ledger boundary.
**Probe:** `tests/Feature/Billing/StripeWebhookTest.php` (:292-398) pins paid-only, async confirmation, replay, subscription-mode, customer mismatch, unknown-price, and malformed-metadata behavior; `tests/Feature/Billing/CreditPackTest.php` (:28-38) pins the second ledger grant returning false. Live Pest is unavailable in this lane (`vendor/` and PHP/Pest executables absent), so these are direct-test references plus deterministic source probes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "fulfillCreditPackCheckout GrantPurchasedCredits creditsForPrice payment_status customer mismatch", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the layered admission order: validate catalog shape, payment state, mode, metadata, tenant/customer binding, then commit through an idempotent ledger. Adapt Stripe/Cashier event names and webhook acknowledgment mechanics. Omit product-specific Stripe price ids and Laravel response helpers. MCP graph and live runner were unavailable; direct source and test reads are the authority for this citation.
