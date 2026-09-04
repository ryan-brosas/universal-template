<!-- capsule-v2 -->
# Payout confirm action guards — what must be validated BEFORE an invoice exists, and which failures are recoverable vs fatal?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What is the ordered guard ladder inside confirmPayoutsAction that a porter must preserve before any money moves?

## confirmPayoutsAction pre-flight ladder
**Path/Symbol:** `apps/web/lib/actions/partners/confirm-payouts.ts:confirmPayoutsAction` (:57-260); selection schema superRefine (:43-49).
**Signature:** server action `{workspaceId, paymentMethodId, cutoffPeriod?, selectedPayoutIds?|excludedPayoutIds?, fastSettlement, amount, fee, total}`.
**Data Shape:** client sends PRECOMPUTED amount/fee/total (from the review screen) — the cron recomputes authoritative numbers later (:179-189 comment "these numbers will be updated later").

### Decisive source
```ts
if (data.selectedPayoutIds?.length && data.excludedPayoutIds?.length) // superRefine :43-49
  ctx.addIssue({ code: "custom", message: "Cannot combine selectedPayoutIds with excludedPayoutIds..." });
...
if (hasExternalPayouts && payoutWebhooks.length === 0)
  throw new Error(`EXTERNAL_WEBHOOK_REQUIRED: This invoice includes at least one external payout,
    which requires an active webhook subscribed to the "payout.confirmed" event...`);
...
if (!mandate) { await stripe.paymentMethods.detach(paymentMethodId);
  throw new Error("No active mandate found for this bank account..."); }
```
(:43-49,:154-158,:193-198)

**Flow:** permission `payouts.write` → workspace stripeId present → fastSettlement plan-gated AND ACH-only → usage-limit check (usage+amount ≤ payoutsLimit) → ≥$10 invoice floor → cutoff only when eligible ≤1000 → external-mode payouts REQUIRE a live `payout.confirmed` webhook (fatal, named error code the UI string-matches) → paymentMethod must belong to THIS customer and be a supported type → direct-debit mandate validated, invalid ⇒ DETACH the method (self-healing: dead mandates disappear from saved methods) → tx create invoice → dispatch tremendous-campaign job if missing → QStash process with dedup id.
**Invariant:** (1) every guard throws BEFORE invoice creation — no orphan invoices from failed validation; the ONE post-create risk (QStash publish failing) is covered by dedup + retry; (2) mandate failure mutates Stripe state (detach) because keeping it guarantees repeat failure; (3) client totals are display-only until the cron overwrites them.
**Probe:** deterministic probe: `grep -n 'EXTERNAL_WEBHOOK_REQUIRED' apps/web/lib/actions/partners/confirm-payouts.ts` = :155; `grep -c 'paymentMethods.detach' apps/web/lib/actions/partners/confirm-payouts.ts` = 1. No upstream unit suite covers this action directly (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "confirmPayoutsAction", limit: 5 });
```

## Verdict
Adopt validate-then-mutate ordering with self-healing detach on dead mandates. Adapt permission names/limits. Omit webhook-required gating if you have no external payout mode.
