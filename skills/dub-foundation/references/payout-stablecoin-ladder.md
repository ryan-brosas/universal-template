<!-- capsule-v2 -->
# Stablecoin payout ladder — how do you pay a crypto wallet through Stripe's money-management API, and why is the fee deducted BEFORE the amount is sent?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What is the exact degradation ladder when a partner's stablecoin (Stripe recipient crypto-wallet) rail breaks mid-flight, and how do fees and pre-funding compose?

## createStablecoinPayout: fee-first netting → account health gates → FA top-up → outbound payment
**Path/Symbol:** `apps/web/lib/partners/create-stablecoin-payout.ts:createStablecoinPayout` (:36-393); helpers `apps/web/lib/stripe/fund-financial-account.ts:13-63`, `create-stripe-outbound-payment.ts:10-56`, `get-stripe-recipient-payout-method.ts:4-26`; v2 client `apps/web/lib/stripe/stripe-v2-client.ts` (`STRIPE_API_VERSION = "2025-09-30.preview"`, schema-typed @better-fetch registry :18-52).
**Signature:** `createStablecoinPayout({ partnerId, invoiceId?, forceWithdrawal? })`; buckets keyed on `stripePayoutId:null ∧ method ∈ {stablecoin, connect}` for backlog but ONLY stablecoin for the current invoice (:78-107).
**Data Shape:** STABLECOIN_PAYOUT_FEE_RATE=0.5%, STABLECOIN_PAYOUT_FIXED_FEE_CENTS=$0.50 (`constants/payouts.ts:27-28`); outbound payment body `{from:{financial_account,currency:"usd"}, to:{recipient,currency:"usdc"}, amount:{value,currency:"usd"}}`.

### Decisive source
```ts
// remove the stablecoin payout fee (0.5%) and withdrawal fee (if applicable) from the total amount
totalTransferableAmount -= totalTransferableAmount * STABLECOIN_PAYOUT_FEE_RATE + withdrawalFee;
totalTransferableAmount = Math.floor(totalTransferableAmount);   // Round down to nearest integer
// ...
if (amountToTransferToFA > 0) await fundFinancialAccount({ amount: amountToTransferToFA, idempotencyKey });
const outboundPayment = await createStripeOutboundPayment({ stripeRecipientId, amount: totalTransferableAmount, ... });
```
(:171-251)
```ts
if (!financialAccountId) throw new Error("STRIPE_FINANCIAL_ACCOUNT_ID is not configured.");
const balance = await stripe.balance.retrieve();
if ((usdAvailable?.amount ?? 0) < amount) throw new Error(`Insufficient balance...`);
... await new Promise((resolve) => setTimeout(resolve, 5000));  // wait for FA availability
```
(fund-financial-account.ts :17-62)

**Flow:** payoutsEnabled/recipient guards → fold buckets → force-withdrawal with empty backlog throws → below-minimum: force ⇒ $0.50 fee; else mark processed + return (same defer contract as Connect rail) → NET the 0.5% fee out of the payout then floor → recipient account CLOSED ⇒ null stripeRecipientId + payoutsEnabledAt=null + release holds (:183-201); missing crypto_wallets capability ⇒ payoutsEnabledAt=null only (:204-227) → transfer backlog total into Dub's Financial Account (balance-checked, idempotent, 5s settle sleep) → create the USD→USDC outbound payment from the FA → stamp `{stripePayoutId, status:"sent"}` → commissions→paid 250-chunked → allSettled side effects → email.
**Invariant:** (1) fees are subtracted from the PARTNER's proceeds before the API call — the funding top-up must cover principal + Stripe's per-payout fixed fee (the router adds count×$0.50 at queue time), otherwise the outbound payment bounces on FA balance; (2) closed account vs missing capability are DIFFERENT failures: closed also clears stripeRecipientId (unrecoverable without re-onboarding); (3) Math.floor guarantees integral cents — a porter using round() could over-send by a cent against the funded amount; (4) every destructive gate still releases invoice holds first so an invoice can complete.
**Probe:** deterministic probe: `grep -c 'markPayoutsAsProcessed(currentInvoicePayouts)' apps/web/lib/partners/create-stablecoin-payout.ts` = 4; `grep -n 'Math.floor(totalTransferableAmount)' apps/web/lib/partners/create-stablecoin-payout.ts` = :176. No upstream unit suite (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "createStablecoinPayout", limit: 5 });
```

## Verdict
Adopt the fee-netted, floor-rounded, pre-funded outbound-payment ladder and the two-tier recipient-health gates. Adapt currency pairs (USDC here), the FA id, and preview-API versioning (schema-typed fetch client is worth copying wholesale). Omit gift-card/Connect alternatives if you have a single rail.
