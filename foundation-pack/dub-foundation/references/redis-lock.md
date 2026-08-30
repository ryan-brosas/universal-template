<!-- capsule-v2 -->
# Token-ownership Redis lock — NX acquire + Lua compare-and-delete release

**Source:** dub AGPL-3.0-or-later (EE dirs separately licensed) `main@873edc5a9727317513c966b8d9b9171794fc89f8`; Codebase Memory `dub`. **Question:** How do you prevent one runner from releasing a lock that expired and was acquired by someone else?

## withRedisLock
**Path/Symbol:** `apps/web/lib/upstash/redis-lock.ts:withRedisLock` (17–42).
**Signature:** `withRedisLock<T>({ key, ttlSeconds, fn }): Promise<T | null>` — `null` means the lock was NOT acquired (another holder active); the wrapped fn's return value is passed through otherwise.
**Data Shape:** lock value is a per-call unique token (`crypto.randomUUID()`), not a constant; release is a Lua compare-and-delete.

### Decisive source
```lua
-- RELEASE_LOCK_SCRIPT
if redis.call("get", KEYS[1]) == ARGV[1] then
  return redis.call("del", KEYS[1])
else
  return 0
end
```
```ts
const token = crypto.randomUUID();
const acquired = await redis.set(key, token, { nx: true, ex: ttlSeconds });
if (!acquired) return null;                 // caller decides what "busy" means
try { return await fn(); }
finally { await redis.eval(RELEASE_LOCK_SCRIPT, [key], [token]); }  // only owner releases
```

**Flow:** SET NX EX with a random token → on failure return null (no throwing, no waiting — contention is signaled by return value) → run fn → in `finally`, EVAL the guard script so the key is deleted ONLY if it still holds this call's token. If the TTL expired mid-run and another runner took the lock, this run's delete is a no-op.
**Invariant:** release is atomic compare-and-delete — never `DEL key` unconditionally; acquisition failure is a VALUE (`null`), not an exception; the release happens in `finally` even when `fn` throws.
**Probe:** no direct unit test file for the lock. Source-grounded probe: `search_graph` resolves `withRedisLock`; port with your own test: take the lock, overwrite the key with a different token, assert the first release does not delete the second holder's key.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "withRedisLock RELEASE_LOCK_SCRIPT", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt NX+EX with a unique value token, Lua compare-and-delete release, null-means-busy signaling, and finally-scoped release; adapt the client (ioredis/Upstash), TTL defaults per use site, and token source. Omit renewal/watchdog logic — this primitive deliberately has none (TTL bounds the critical section). Caveat: no direct upstream test for this seam.
