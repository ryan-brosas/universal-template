<!-- capsule-v2 -->
# Program-owner payout reminders — how do you nudge the PAYING side about pending payouts, with a month-end window, weekday gate, and custom-minimum handling?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What selects a program for an owner-facing payout reminder and why are custom-minimum programs aggregated separately?

## reminders/program-owners route: calendar gate → two-tier aggregation → recent-invoice suppression
**Path/Symbol:** `apps/web/app/(ee)/api/cron/payouts/reminders/program-owners/route.ts:GET` (:14-214).
**Signature:** cron expression `0 13 25-31,1-5 * *` (days 25-31 + 1-5 at 13:00 UTC) PLUS an in-code weekend guard (getUTCDay 0/6 ⇒ skip) — cron narrows days, code enforces weekdays.
**Data Shape:** default tier = groupBy pending payouts (`amount > 0`, partner onboarded, program active, EXCLUDING programs with minPayoutAmount>0); custom tier = per-program aggregate with `amount ≥ program.minPayoutAmount`.

### Decisive source
```ts
// only send notifications for programs that:
// - have a total payout amount greater than or equal to $10 (INVOICE_MIN_PAYOUT_AMOUNT_CENTS)
// - have not paid out any invoices in the last 2 weeks
return (
  invoiceTotal >= INVOICE_MIN_PAYOUT_AMOUNT_CENTS ||
  recentPaidInvoicesForProgram.length === 0 );
```
(:121-130; suppression set = invoices created in last 14 days :104-113)

**Flow:** weekend short-circuit → two-tier pending aggregation (custom-min programs need PER-PROGRAM thresholds so they can't share one groupBy predicate) → suppress programs that invoiced within 14 days (they're actively paying; nagging reads as distrust) → resolve workspace OWNERS only → chunk-100 batch emails "N partners awaiting your payout" → done (no timestamp stamping needed: the calendar window IS the cadence).
**Invariant:** (1) eligibility uses each program's OWN minimum, not a global floor — a $50-minimum program's $20 payouts must not trigger reminders; (2) owners receive AGGREGATES ({amount, partnersCount}) never partner identities; (3) OR-semantics on the notify filter mean an under-$10 program still reminds if it has NEVER paid (new-program nudge).
**Probe:** deterministic probe: `grep -n 'dayOfWeek === 0 || dayOfWeek === 6' 'apps/web/app/(ee)/api/cron/payouts/reminders/program-owners/route.ts'` = :22; `grep -c 'minPayoutAmount' 'apps/web/app/(ee)/api/cron/payouts/reminders/program-owners/route.ts'` = 4. No upstream unit suite (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "ProgramPayoutReminder", limit: 5 });
```

## Verdict
Adopt calendar-window-plus-code-weekday gating, per-program minimum tiers, and recent-activity suppression. Adapt windows/thresholds. Omit if your product has no owner-side payment step.
