<!-- capsule-v2 -->
# FX conversion with cached rates — how do you normalize multi-currency provider data to USD, and when is a live quote required instead?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What are the two currency-conversion paths (import-time cached rates vs charge-time live Stripe quotes) and their failure postures?

## convertCurrencyWithFxRates + createFxQuote + fx-rates cron
**Path/Symbol:** `apps/web/lib/analytics/convert-currency.ts:convertCurrencyWithFxRates` (:37-69, zero-decimal ×100 rule :61-63); live quote `apps/web/lib/stripe/create-fx-quote.ts:createFxQuote` (:9-37); rate refresh `apps/web/app/(ee)/api/cron/fx-rates/route.ts`; consumer example `apps/web/lib/tolt/import-commissions.ts:236-254`.
**Signature:** `convertCurrencyWithFxRates({currency, amount, fxRates})` where fxRates = Redis hash `fxRates:usd` (`redis.hgetall`); live path posts form-encoded `from_currencies[]/to_currency/lock_duration=none` to `/v1/fx_quotes`.
**Data Shape:** import path converts sale amount AND earnings independently; payout processing path converts the CHARGE (not payouts) and applies FOREX_MARKUP_RATE=0.5% on top.

### Decisive source
```ts
let saleAmount = Number(sale.revenue ?? 0);
if (programCurrency.toUpperCase() !== "USD" && fxRates) {
  const { amount: convertedAmount } = convertCurrencyWithFxRates({
    currency: programCurrency, amount: saleAmount, fxRates });
  saleAmount = convertedAmount;
}
```
(import-commissions.ts :236-245 — missing rates silently keep the ORIGINAL currency amount)
```ts
const exchangeRate = fxQuote.rates[currency].exchange_rate;
if (!exchangeRate || exchangeRate <= 0)
  throw new Error(`Failed to get exchange rate from Stripe for ${currency}.`);
const convertedTotal = Math.round((totalToCharge / exchangeRate) * (1 + FOREX_MARKUP_RATE));
```
(process-payouts.ts :200-218)

**Flow:** a daily cron refreshes the Redis `fxRates:usd` hash from a market source → historical imports convert at IMPORT-TIME snapshot rates and tolerate staleness (best-effort) → but money MOVEMENT never trusts them: charging a SEPA/ACSS invoice fetches a live Stripe fx_quote, validates the rate is present AND positive, rounds after multiplying by (1+markup), and throws on any gap.
**Invariant:** (1) two tolerance classes: analytics/import data prefers stale-but-present over failing (missing rate ⇒ original currency returned untouched); balance-moving operations prefer failing over stale — porters who reuse the Redis cache for charges will misprice invoices; (2) zero-decimal currencies (JPY etc.) multiply by 100 AFTER dividing, or the result is off by 100×; (3) markup lands INSIDE the round() so the fee survives unit truncation; (4) direction convention: rates hash is keyed `fxRates:usd` (to-USD), while Stripe's quote divides by a to-USD rate for a from-currency charge — inverting one of these is the classic bug.
**Probe:** deterministic probe: `grep -n 'FOREX_MARKUP_RATE' 'apps/web/app/(ee)/api/cron/payouts/process/process-payouts.ts' | head -2` = :3,:211; `grep -c "fxRates:usd" apps/web/lib/tolt/import-commissions.ts` = 1. No upstream unit suite covers the conversion paths directly (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "createFxQuote", limit: 5 });
```

## Verdict
Adopt the dual-tolerance split (cached-for-analytics, quoted-for-money) verbatim. Adapt providers and markup. Omit the import-time path if your ledger is USD-native.
