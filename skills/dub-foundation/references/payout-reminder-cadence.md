<!-- capsule-v2 -->
# Payout reminder nudge — how do you re-engage partners who have money waiting but haven't onboarded, without spamming them?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What selects a partner for a payout-reminder email and how is the 3-day cadence enforced in the query itself?

## reminders/partners route: groupBy eligible sums → last-reminded gate → batch email
**Path/Symbol:** `apps/web/app/(ee)/api/cron/payouts/reminders/partners/route.ts:GET` (:21-100+); constants `MIN_PAYOUT_AMOUNT_FOR_REMINDER` (`lib/constants/misc.ts`) + `PAYOUT_SUPPORTED_COUNTRIES`.
**Signature:** daily cron (GET/withCron); `prisma.payout.groupBy({by:["partnerId","programId"], where:{...}, _sum:{amount:true}, orderBy:{_sum:{amount:"desc"}}, take:1000})`.
**Data Shape:** payout statuses counted = pending|processing|processed|failed (NOT sent/completed); partner gates = payoutsEnabledAt:null ∧ country supported ∧ (`connectPayoutsLastRemindedAt:null ∨ ≤ now−3d`).

### Decisive source
```ts
partner: {
  payoutsEnabledAt: null,
  country: { in: PAYOUT_SUPPORTED_COUNTRIES.map((c) => c.code) },
  OR: [
    { connectPayoutsLastRemindedAt: null },
    { connectPayoutsLastRemindedAt: { lte: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000) } } ] },
```
(:41-52)

**Flow:** groupBy aggregates unpaid-but-claimable payout sums per partner-program, biggest debtors first, excluding dub's own ACME/demo programs and programs mid-migration → fetch partner + program details for the page → queue batch emails ("you have $X waiting — set up payouts") → stamp `connectPayoutsLastRemindedAt` so the WHERE-clause cadence self-enforces on the next run; full-page ⇒ walker-style requeue. A program-owner twin route mirrors the pattern for owners owing payouts.
**Invariant:** (1) the cadence lives in the SELECTION predicate, not in app logic — any row that skips emailing for another reason must still update the timestamp or it will be retried immediately next run; (2) only statuses meaning "money they could claim" trigger nudges; completed/sent payouts never remind; (3) amount floor prevents nickel-and-dime emails.
**Probe:** deterministic probe: `grep -n 'connectPayoutsLastRemindedAt' 'apps/web/app/(ee)/api/cron/payouts/reminders/partners/route.ts' | head -3` = :42,:44,:157; stamp = updateMany :181-189; `grep -c 'groupBy' 'apps/web/app/(ee)/api/cron/payouts/reminders/partners/route.ts'` = 1. No upstream unit suite (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "connectPayoutsLastRemindedAt", limit: 5 });
```

## Verdict
Adopt predicate-level cadence gating with post-send timestamp stamps for any recurring nudge system. Adapt floors/cadences. Omit the country allowlist when your rails are global.
