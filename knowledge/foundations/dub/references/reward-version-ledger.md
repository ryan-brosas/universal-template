<!-- capsule-v2 -->
# Reward version ledger — Redis monotonic versions that invalidate in-flight batch sweeps

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** How does a reward edit made mid-sweep cancel the stale batches still queued in QStash?

## INCR+EXPIRE version counter and the staleness predicate
**Path/Symbol:** `apps/web/lib/api/rewards/reward-version.ts:incrementRewardVersion` (:16-31) + `isStaleRewardVersion` (:33-50) + `getRewardVersionKey` (:6-14).
**Signature:** `getRewardVersionKey({groupId, event}): string`; `incrementRewardVersion({groupId, event}): Promise<number>`; `isStaleRewardVersion({version, groupId, event}): Promise<boolean>`.
**Data Shape:** Redis key `reward-version:<groupId>:<event>` (24h TTL); values are integers; missing key ⇒ NOT stale.

### Decisive source
```ts
const version = await redis.incr(key);
await redis.expire(key, REWARD_VERSION_TTL_SECONDS);
return version;
```
(reward-version.ts :28-30)

```ts
const currentVersion = await redis.get(key);

return currentVersion != null && version < Number(currentVersion);
```
(reward-version.ts :47-49)

**Flow:** every reward create/update/delete calls incrementRewardVersion (via queueRewardProcessing when version isn't supplied) → the job body carries its mint-time version → each cron batch re-checks isStaleRewardVersion before touching enrollments → a newer reward change bumped the key ⇒ older batches self-abort. EXPIRE refreshes on every INCR so the TTL is sliding-from-last-change; equal versions are NOT stale (`<` not `<=`) so the final batch of a sweep completes.
**Invariant:** strict `<` is load-bearing — using `<=` would kill the last legitimate batch; the 24h TTL means a version gap >24h silently loses invalidation protection (acceptable: sweeps finish in minutes); per-(group,event) keying isolates click changes from sale sweeps.
**Probe:** deterministic probes (repo root): `grep -n 'reward-version:' apps/web/lib/api/rewards/reward-version.ts` → :13; `grep -n "version < Number" apps/web/lib/api/rewards/reward-version.ts` → :49; `grep -n 'currentVersion != null' apps/web/lib/api/rewards/reward-version.ts` → :49; `grep -c 'redis' apps/web/lib/api/rewards/reward-version.ts` → 4; `grep -n 'REWARD_VERSION_TTL_SECONDS = 24' apps/web/lib/api/rewards/reward-version.ts` → :4. No upstream unit suite for this file (recorded caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "incrementRewardVersion", limit: 5, fields: ["signature", "name", "file"] });
```
(also live: `isStaleRewardVersion` → same file :33-50.)

## Verdict
Adopt INCR+sliding-EXPIRE versioning with the strict-less-than staleness predicate and missing-key-equals-fresh rule. Adapt Redis client. Omit nothing.
