<!-- capsule-v2 -->
# Redis soft-delete cache with single-flight connect — how do you cache hot entities and invalidate across a fleet without stale reads?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How does the fetch/soft-delete cache contract work, and how is reconnection deduplicated?

## redis-soft-delete-cache
**Path/Symbol:** `src/lib/redis.ts:UmamiRedisClient :12-88 (fetch :73-83, remove :85-87), getClient single-flight :91-135`; consumer `src/lib/load.ts:fetchWebsite :5-16`.
**Signature:** `fetch(key, query, time?) -> value|null`; `remove(key, soft=true)` stores sentinel `'__DELETED__'` instead of deleting; DEFAULT_TTL=3600.
**Data Shape:** values JSON-serialized; DELETED sentinel distinguishes "known deleted" from "never cached".

### Decisive source
```ts
async fetch(key: string, query: () => Promise<any>, time?: number) {
  const result = await this.get(key);
  if (result === DELETED) return null;          // negative cache: don't re-query
  if (!result && query) {
    const data = await query();
    if (data) await this.set(key, data, time);  // only cache FOUND entities
    return data;
  }
  return result;
}
// connect() dedupe:
if (connectPromise) return connectPromise;      // one in-flight connect per process
connectPromise = (async () => { try { await originalConnect(); }
  catch (e) { redis.isConnected = false; throw e; } finally { connectPromise = null; } })();
// 'end'/'reconnecting' events reset isConnected so the next op re-dials.
```

**Flow:** read → sentinel ⇒ null without DB hit; miss ⇒ run query ⇒ cache only non-null (deleted rows are never re-cached as absent). Writers call `remove(key, true)` on entity update so OTHER nodes' caches learn deletion via TTL'd sentinel rather than staying stale until their own TTL.
**Invariant:** caching only truthy results is what makes the sentinel safe — if you start caching `null`, the DELETED check can't distinguish states. The connectPromise must be cleared in `finally` or one failed connect poisons every future request.
**Probe:** structural pins: `grep -n "__DELETED__" src/lib/redis.ts src/lib/load.ts | head -2` → :13 in redis.ts; `grep -c "connectPromise" src/lib/redis.ts` → ≥4 lines.
**Probe:** `grep -n "86400" src/lib/load.ts` → :10 and :20 (24h entity TTLs).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "fetch remove DELETED soft delete redis", limit: 10 });
```

## Verdict
Adopt sentinel-based soft invalidation + single-flight reconnect for shared read caches; adapt TTLs; omit the white-label/account raw-get consumers which bypass fetch() deliberately.
