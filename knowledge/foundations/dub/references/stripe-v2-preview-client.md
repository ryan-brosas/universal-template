<!-- capsule-v2 -->
# Stripe v2 preview client — how do you call Stripe's money-management APIs before the SDK supports them, and what does the schema-typed fetch registry buy you?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** How are the /v2 core-accounts and money-management endpoints wired, and where do FX quotes bypass the SDK entirely?

## stripeV2Fetch registry + createFxQuote raw form POST
**Path/Symbol:** `apps/web/lib/stripe/stripe-v2-client.ts:stripeV2Fetch` (:18-70); `apps/web/lib/stripe/create-fx-quote.ts:createFxQuote` (:9-37); STRIPE_API_VERSION `"2025-09-30.preview"` (:17).
**Signature:** `createFetch({baseURL, headers, schema: createSchema({"<path>": {method,input,output,query?}}, {strict:true})})` from `@better-fetch/fetch`; callers destructure `{data,error}`.
**Data Shape:** registered endpoints: `/v2/core/accounts` (POST recipient account), `/v2/core/accounts/:id` (GET), `/v2/core/account_links`, `/v2/money_management/outbound_payments` (+`:id`), `/v2/money_management/payout_methods` (list w/ limit query), and a `/v1/payouts` POST escape hatch ("payout_method is a preview feature and not currently available in our current SDK version" :46-48).

### Decisive source
```ts
export const stripeV2Fetch = createFetch({
  baseURL: "https://api.stripe.com",
  headers: { Authorization: `Bearer ${process.env.STRIPE_SECRET_KEY}`,
             "Stripe-Version": STRIPE_API_VERSION },
  schema: createSchema({ /* endpoint → zod input/output map */ }, { strict: true }),
});
```
(:19-52)
```ts
body.append("from_currencies[]", fromCurrency);
body.append("to_currency", toCurrency);
body.append("lock_duration", "none");
const fxQuoteResponse = await fetch("https://api.stripe.com/v1/fx_quotes", {
  method: "POST",
  headers: { Authorization: `Bearer ${...}`,
    "Stripe-Version": "2025-05-28.basil;fx_quote_preview=v1", ... } });
```
(create-fx-quote.ts :14-30)

**Flow:** every stablecoin-plane call goes through the typed client (`getStripeRecipientAccount`, `getStripeRecipientPayoutMethod` adding per-request `Stripe-Context: stripeRecipientId`, outbound payments) so responses arrive PARSED against zod schemas — provider shape drift fails at the boundary, not at money math. FX quotes can't use this client (different pinned preview version + form-encoded array params), so they run as a raw fetch with their own schema.parse; failure wraps the whole payload into the error message.
**Invariant:** (1) two Stripe-Version values coexist deliberately — the v2 client pins one preview, fx_quotes another; mixing them on one client silently breaks feature flags; (2) strict schema mode means unknown fields REJECT — porters upgrading endpoints must widen schemas consciously; (3) the recipient header (`Stripe-Context`) is what scopes payout-method listing to a partner's account.
**Probe:** deterministic probe: `grep -n 'STRIPE_API_VERSION = ' apps/web/lib/stripe/stripe-v2-client.ts` = :17; `grep -c 'fx_quote_preview=v1' apps/web/lib/stripe/create-fx-quote.ts` = 1. No upstream unit suite covers these clients (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "stripeV2Fetch", limit: 5 });
```

## Verdict
Adopt the schema-typed preview-client pattern (and its version-pinned raw-fetch sibling) for any provider API ahead of official SDKs. Adapt endpoint maps and versions. Omit the account-links entries unless you onboard recipients.
