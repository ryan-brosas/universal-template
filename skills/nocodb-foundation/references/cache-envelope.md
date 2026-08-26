<!-- capsule-v2 -->
# Cache object envelope — how does the cache store values so any entry knows which list keys reference it, and why do lists expire before their children?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does a cache entry know which parent lists point at it, and how do TTLs keep parent/child sets consistent?

## value+parentKeys+timestamp envelope
**Path/Symbol:** `packages/nocodb/src/cache/CacheMgr.ts:prepareValue/getParents/set/refreshTTL` (92-162, 573-607, 614-678).
**Signature:** `prepareValue({value, parentKeys, newKey?, timestamp?}): {value, parentKeys, timestamp}`; `set(key, value, {skipPrepare?, timestamp?}): Promise<any>`.
**Data Shape:** simple key → stringified JSON `{value: {...}, parentKeys: ["nc:<org>:<scope>:<id>:list", ...], timestamp: <ms>}` stored with `EX NC_REDIS_TTL`; list key (`*:list`) → Redis SET of child key strings with `EX NC_REDIS_TTL - 60`.

### Decisive source
```ts
// arrays are lists-of-keys, never payloads
if (Array.isArray(value) && value.length) {
  return new Promise((resolve) => {
    this.client.pipeline()
      .sadd(key, value)
      // - 60 seconds to avoid expiring list before any of its children
      .expire(key, NC_REDIS_TTL - 60)
      .exec(...);
  });
}
if (!skipPrepare) {
  const keyValue = await this.getRaw(key);
  value = this.prepareValue({ value, parentKeys: this.getParents(keyValue), timestamp });
}
// read path: refresh lazily instead of losing warm entries
if (!skipTTL && o.timestamp) {
  const diff = Date.now() - o.timestamp;
  if (diff > NC_REDIS_GRACE_TTL * 1000) { await this.execRefreshTTL(key); }
}
```

**Flow:** every scalar write wraps the payload with its back-pointers and a timestamp; reads older than the grace TTL rewrite themselves (and cascade to parents via `refreshTTL`) so a hot cache never goes cold. `setList` stamps all children with one shared timestamp then stores the child-key SET as the parent.
**Invariant:** the `-60s` list TTL is non-negotiable — a parent list must NEVER outlive its children, or `mget` returns nulls and triggers the self-heal fallback. Writes preserve inherited `parentKeys` (read old raw first) so an entry referenced by several lists keeps all back-pointers when updated through one of them.
**Probe:** no unit test upstream. Source-grounded probe: `CacheMgr.ts:114-134` — array values always take the sadd+expire(NC_REDIS_TTL-60) pipeline; `:63-68` — grace-TTL lazy refresh on read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "CacheMgr prepareValue getParents refreshTTL set", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the `{value,parentKeys,timestamp}` envelope, list-expires-before-children TTL skew, and read-time lazy refresh; adapt key prefix scheme (`nc:<org>:<scope>:`), TTL constants, and storage backend to host; omit the org placeholder until multi-org exists. Coverage caveat: no in-repo tests; source-grounded.
