<!-- capsule-v2 -->
# Force-withdrawal orchestration — how do you let a partner (or a 90-day sweeper) withdraw below-minimum earnings without letting concurrent withdrawals double-pay?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What locks and minimum-fee rules govern manual withdrawals across the three internal rails?

## forceWithdrawal: NX lock → rail dispatch; daily sweeper reuses it
**Path/Symbol:** `apps/web/lib/actions/partners/force-withdrawal.ts:forceWithdrawal` (:52-76) + action wrapper (:17-50); daily sweep `apps/web/app/(ee)/api/cron/payouts/force-withdrawals/route.ts` (:22-110); per-rail force branches already covered in payout-connect-transfer / payout-stablecoin-ladder / payout-tremendous-giftcards.
**Signature:** `forceWithdrawal(partner: Pick<Partner,"id"|"defaultPayoutMethod">)`; lock `force-withdrawal:lock:${partnerId}` via `redis.set(...,{nx:true, ex:60})`, released in finally.
**Data Shape:** allowed rails for force = connect|stablecoin|tremendous (paypal NOT forceable); MIN_FORCE_WITHDRAWAL=$1, BELOW_MIN fee=$0.50.

### Decisive source
```ts
const acquired = await redis.set(lockKey, "1", { nx: true, ex: 60 });
if (!acquired) throw new Error("A withdrawal is already in progress...");
try {
  if (partner.defaultPayoutMethod === "stablecoin") await createStablecoinPayout({ partnerId, forceWithdrawal: true });
  else if (... "connect") await createStripeTransfer({ partnerId, forceWithdrawal: true });
  else if (... "tremendous") await sendTremendousPayouts({ partnerId, forceWithdrawal: true });
} finally { await redis.del(lockKey); }
```
(:44-75)

**Flow:** action validates permission + default-method presence before locking; the lock makes any concurrent withdrawal attempt fail LOUDLY rather than queue behind a possibly-stuck provider call; each rail then applies its own force semantics (fee instead of defer, throw on dead accounts). The sweeper finds partners with processed payouts untouched ≥90 days (default method connect/stablecoin only), calls the same `forceWithdrawal` under allSettled, and self-requeues in batches of 20.
**Invariant:** (1) the lock is per-PARTNER, not global — different partners withdraw concurrently; (2) fixed-value lock ("1", no owner token) is acceptable here because the critical section is short and the 60s TTL bounds worst-case staleness — do not copy this into long-running sections without upgrading to token release (see payout-amount-reconciliation's withRedisLock); (3) paypal partners cannot self-force because that rail has no sub-minimum path.
**Probe:** deterministic probe: `grep -n 'nx: true, ex: 60' apps/web/lib/actions/partners/force-withdrawal.ts` = :45; `grep -c 'BATCH_SIZE = 20' 'apps/web/app/(ee)/api/cron/payouts/force-withdrawals/route.ts'` = 1. No upstream unit suite covers this file (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "forceWithdrawal", limit: 5 });
```

## Verdict
Adopt the loud-fail per-entity NX lock plus rail dispatch with per-rail force semantics. Adapt TTL to your provider latencies (upgrade to owner-token release for slow rails). Omit the 90-day sweeper unless you hold partner balances.
