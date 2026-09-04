<!-- capsule-v2 -->
# Treasury sweep & owner nudges — what sweeps the platform's own Stripe balance safely, and how does the program-owners reminder twin differ from partner reminders?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** Which nudge/sweep crons exist around payouts beyond the partner reminder, and what distinguishes them?

## trigger-withdrawal: treasury sweep
**Path/Symbol:** `apps/web/app/(ee)/api/cron/trigger-withdrawal/route.ts:GET` (:12-70); runs 2×/day; NOT partner-facing (my earlier draft mislabeled it as per-partner — corrected).
**Signature:** no input; reads platform Stripe balance + SUM of processing|processed payouts.
**Data Shape:** `balanceToWithdraw = netBalance − payoutsToBeSent − reservedBalance($30,000)`; negative pending balance SUBTRACTS from available (:36-39, x-slack-ref comment).

### Decisive source
```ts
const currentNetBalance = currentPendingBalance < 0
    ? currentAvailableBalance + currentPendingBalance : currentAvailableBalance;
const payoutsToBeSent = payoutsToBeSentData._sum.amount ?? 0;
const reservedBalance = 30_000_00; // keep at least $30,000 in the account
const balanceToWithdraw = currentNetBalance - payoutsToBeSent - reservedBalance;
if (balanceToWithdraw <= 0) return logAndRespond(`...skipping...`);
await stripe.payouts.create({ amount: balanceToWithdraw, currency: "usd" });
```
(:33-64)

**Flow:** twice daily the PLATFORM's own account sweeps everything above a $30k operating reserve out to the company bank, reserving exactly what it still owes partners (sum of processing+processed payout rows) and netting negative pending balances.
**Invariant:** (1) liability-aware sweeping: the reserved term is computed from dub's OWN ledger rows, not Stripe's view, so in-flight rails are never swept; (2) negative pending (recent disputes) reduces today's withdrawal instead of over-drafting.
**Probe:** deterministic probe: `grep -n 'reservedBalance = 30_000_00' 'apps/web/app/(ee)/api/cron/trigger-withdrawal/route.ts'` = :34. No upstream unit suite (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "trigger-withdrawal", limit: 5 });
```

## Verdict
Adopt liability-aware treasury sweeping (own-ledger reservation + negative-pending netting) and the pre-captured cadence stamps from payout-reminder-cadence. Adapt reserve amounts. Omit if you don't hold a platform balance.
