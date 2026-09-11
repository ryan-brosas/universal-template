<!-- capsule-v2 -->
# Payout fee waiver & method surcharge — how do workspace fee waivers interact with card hard costs and fast-ACH flat fees when computing an invoice's single fee number?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What is the exact arithmetic that turns a payout amount + plan fee + payment method into `fee`, and which parts can never be waived?

## calculatePayoutFeeForMethod + calculatePayoutFeeWithWaiver
**Path/Symbol:** `apps/web/lib/stripe/payment-methods.ts:calculatePayoutFeeForMethod` (:8-26); `apps/web/lib/partners/calculate-payout-fee-with-waiver.ts:calculatePayoutFeeWithWaiver` (:16-53); constants `apps/web/lib/constants/payouts.ts:25-30` (CARD 3%, STABLECOIN 0.5%+$0.50, FAST_ACH $25, FOREX 0.5%).
**Signature:** `calculatePayoutFeeForMethod({paymentMethod, payoutFee}) → number|null` (card/link ⇒ payoutFee+3% hard cost; direct debits ⇒ payoutFee; else throw); `calculatePayoutFeeWithWaiver({payoutAmount, payoutFee, payoutFeeWaiverLimit, payoutFeeWaiverUsage, paymentMethod}) → {fee, feeFreeAmount, feeChargedAmount, feeWaiverRemaining}`.
**Data Shape:** waiverLimit=0 means NO waiver program (feeFreeAmount=0); usage counters increment on the WORKSPACE row after a successful charge (`process-payouts.ts:249-260`).

### Decisive source
```ts
const nonWaivableFeeRate = paymentMethod === "card" ? CARD_PAYOUT_HARD_COST_RATE : 0;
const waivableFeeRate = payoutFee - nonWaivableFeeRate;
const fastAchFee = paymentMethod === "ach_fast" ? FAST_ACH_FEE_CENTS : 0;
if (payoutFeeWaiverLimit === 0) { feeWaiverRemaining = 0; feeFreeAmount = 0; feeChargedAmount = payoutAmount; }
else {
  feeWaiverRemaining = Math.max(0, payoutFeeWaiverLimit - payoutFeeWaiverUsage);
  feeFreeAmount = Math.min(payoutAmount, feeWaiverRemaining);
  feeChargedAmount = payoutAmount - feeFreeAmount;
}
const fee = Math.round(payoutAmount * nonWaivableFeeRate)
          + Math.round(feeChargedAmount * waivableFeeRate)
          + fastAchFee;
```
(:23-52)

**Flow:** method rate first (card hard cost rides on TOP of the plan fee and is subtracted from it for waiver purposes) → waiver budget = limit − usage floored at 0 → free slice = min(amount, budget) → fee composes three independent terms: unwaivable on EVERYTHING + waivable rate on only the charged slice + flat fast-ACH surcharge. The caller then writes `{amount, externalAmount, fee, total}` to the invoice and increments BOTH workspace usage counters (`payoutsUsage` by full amount, `payoutFeeWaiverUsage` by only the free slice) — so waivers deplete exactly by what they covered.
**Invariant:** (1) the waivable rate is DERIVED (`planFee − hardCost`), never stored — porters who store a second rate will drift from plan changes; (2) rounding happens per-term before summing; (3) waiver accounting is consumed post-success, not pre-decremented — a failed charge leaves the budget intact.
**Probe:** deterministic probe: `grep -n 'nonWaivableFeeRate\|waivableFeeRate' apps/web/lib/partners/calculate-payout-fee-with-waiver.ts | head -3` = :24-25; `grep -c 'Math.round' apps/web/lib/partners/calculate-payout-fee-with-waiver.ts` = 2. No upstream unit suite covers these pure functions directly (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "calculatePayoutFeeWithWaiver", limit: 5 });
```

## Verdict
Adopt the three-term fee composition and derived-waivable-rate rule verbatim. Adapt rates/limits. Omit fast-ACH if you have no settlement-speed upsell.
