<!-- capsule-v2 -->
# Payout amount reconciliation — how do you keep a denormalized payout.amount equal to SUM(commissions) when concurrent attaches race, and how does the sweeper find drift?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What runs every minute to repair payout amounts, and why can it safely delete empty payouts?

## reconcile-amounts cron: Redis-lock → 2-minute lookback scan → groupBy diff → tx repair
**Path/Symbol:** `apps/web/app/(ee)/api/cron/payouts/reconcile-amounts/route.ts:GET` (:22-121); repair `apps/web/lib/api/commissions/reconcile-payout-amounts.ts:reconcilePayoutAmounts` (:5-72); lock primitive `apps/web/lib/upstash/redis-lock.ts:withRedisLock` (:14-37); retally twin `apps/web/lib/payouts/retally-payouts-amount.ts:retallyPayoutsAmount` (:3-29).
**Signature:** `withRedisLock({key,ttlSeconds,fn}): Promise<T|null>` (null = someone else holds); `reconcilePayoutAmounts(payoutIds)` chunks of 10 inside `$transaction`.
**Data Shape:** scan window = payouts with `updatedAt ≥ now−2min ∧ status:"pending"`, keyset-paged `id > startingAfter` take 500; mismatch row = `{id, payoutAmount, commissionSum, diff}`.

### Decisive source
```ts
const RELEASE_LOCK_SCRIPT = `
  if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
  else
    return 0
  end`;
const token = crypto.randomUUID();
const acquired = await redis.set(key, token, { nx: true, ex: ttlSeconds });
if (!acquired) return null;
try { return await fn(); }
finally { await redis.eval(RELEASE_LOCK_SCRIPT, [key], [token]); }  // owner-only release
```
(redis-lock.ts :1-36)
```ts
await tx.payout.deleteMany({ where: { id: { in: toDelete }, status: { in: MUTABLE_PAYOUT_STATUSES } } });
await Promise.all(toUpdate.map(({ id, amount }) =>
  tx.payout.update({ where: { id, status: { in: MUTABLE_PAYOUT_STATUSES } }, data: { amount } })));
```
(reconcile-payout-amounts.ts :47-66)

**Flow:** every minute the cron takes the `lock:payouts:reconcile-amounts` NX lock (TTL 60s; another holder ⇒ "skipping", NOT an error) → keyset-scan recently-touched pending payouts → ONE groupBy over their commissions builds a Map<payoutId,sum> → rows where `amount !== sum` are logged via console.table and repaired in 10-id transactions: zero-sum pending payouts are DELETED (they were auto-created empties that lost their claim), others re-stamped to the DB truth — both writes re-guarded by MUTABLE_PAYOUT_STATUSES so a payout confirmed to processing mid-repair cannot be mutated or deleted. The one-off `retallyPayoutsAmount` twin does the same per-id without lock/tx for manual repairs.
**Invariant:** (1) reconciliation is CONVERGENT not transactional — it assumes some writer (aggregation claim) already serializes commission attachment and only fixes the cached sum afterward; (2) deletion is legal ONLY under the mutable-status guard because a non-empty payout must never vanish while referenced by a processing invoice; (3) keyset pagination (`id > last`) tolerates inserts during the scan unlike offset paging.
**Probe:** deterministic probe: `grep -c 'MUTABLE_PAYOUT_STATUSES' apps/web/lib/api/commissions/reconcile-payout-amounts.ts` = 2; `grep -n 'LOCK_TTL_SECONDS = 60\|LOOKBACK_MINUTES = 2' 'apps/web/app/(ee)/api/cron/payouts/reconcile-amounts/route.ts'` = :13-14. No upstream unit suite (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "withRedisLock", limit: 5 });
```

## Verdict
Adopt the token-locked convergent sweeper (NX + Lua compare-and-delete + null-means-busy) and the guarded delete-or-restamp repair for any denormalized aggregate kept consistent by cron. Adapt windows/TTLs and chunk sizes. Omit dub's console.table diagnostics.
