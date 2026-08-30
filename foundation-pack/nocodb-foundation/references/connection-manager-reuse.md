<!-- capsule-v2 -->
|# connection-manager reuse — how do introspection clients share one knex pool per source, and why is the cache key composite?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How does NcConnectionMgrv2 hand SqlClientFactory an existing pool, what wire-level typeCast does it install, and what invalidation contract must survive a port?

## connection-manager reuse
**Path/Symbol:** `packages/nocodb/src/utils/common/NcConnectionMgrv2.ts` — `connectionKey` (:46–48), LRU + destroy-on-evict (:24–33), Redis staleness (`RedisVersionTracker 'SOURCE_CONN_VER'`) :66–95, `stashDbMajorVersion` (:106–126), `get()` BIT/NEWDECIMAL typeCast (:145–166), `getSqlClient` (:185–190).
**Signature:** `connectionKey(source) = \`${source.base_id}:${source.id}\``; `getSqlClient(source, knex?) → SqlClientFactory.create({knex, ...connectionConfig})`.
**Data Shape:** LRUMap capped `NC_CONNECTION_CACHE_MAX_SIZE||500`; evicted entries `.destroy()`ed via asyncClear callback.

### Decisive source
```ts
// :42–46 — the incident that forced the composite key (comment verbatim):
// Source ids are unique per base, not instance-wide — the sources table's PK
// is `(base_id, id)`. Keying live connections on the bare id let a source in
// one base be served another base's cached connection.
protected static connectionKey(source: SourceIdentity): string {
  return `${source.base_id}:${source.id}`;
}

// :145–160 — driver-level value coercion installed ONCE on the shared pool:
typeCast(field, next) {
  const res = next();
  if (res && res instanceof Buffer) {          // mysql BIT / binary
    const hex = [...res].map(v => ('00'+v.toString(16)).slice(-2)).join('');
    if (field.type == 'BIT') return parseInt(hex, 16);   // bit → integer
    return hex;                                           // other buffers → hex string
  }
  if (field.type == 'NEWDECIMAL') return res && parseFloat(res);  // decimal → float
  return res;
}

// :186–190 — the reuse contract this capsule exists for:
public static async getSqlClient(source: Source, _knex = null) {
  const knex = _knex || (await this.get(source));
  return SqlClientFactory.create({ knex, ...(await source.getConnectionConfig()) });
}
// KnexClient ctor :153–162 then honors connectionConfig.knex — NO second pool.
```
Invalidation ladder: `resetSource` deletes local ref THEN bumpAndSyncs the Redis key; every other server's `get()` runs checkSourceStaleness FIRST and destroys its local copy when the version moved. `stashDbMajorVersion` reads `source.meta.dbVersion` (populated by populateMeta via SqlClient.version(), object OR JSON-string meta) and writes `(knex.client.config).nocoDbMajorVersion` so dialect-aware code reads it with zero round-trips.

**Flow:** any service needing introspection asks getSqlClient → manager returns cached XKnex (staleness-checked) → factory wraps the SAME handle in a dialect client → all schema DDL/introspection rides the identical pool the ORM query layer uses → config changes funnel through resetSource or the whole cache goes stale.

**Invariant:** (1) The composite key is security-adjacent, not cosmetic — bare-id keys cross-wire tenants' databases. (2) getSqlClient MUST pass the shared knex in `connectionConfig.knex`; constructing `SqlClientFactory.create(config)` bare opens an unmanaged second pool per call. (3) Delete-before-bump ordering in resetSource is deliberate: delete first so THIS server can't re-cache mid-sync, then bump-and-sync so concurrent gets elsewhere create fresh without re-triggering. (4) The mysql typeCast lives at pool level — clients built on this handle receive coerced values everywhere; a porter who re-adds per-query casts double-converts. (5) dbVersion stash tolerates stringified meta and silently skips absent versions (lazy detection fallback), never throws.

**Probe:** runner BLOCKED (manager has no upstream spec) → deterministic probes at pin: `sed -n '42,48p' packages/nocodb/src/utils/common/NcConnectionMgrv2.ts` shows the PK comment + template key; `grep -c "NEWDECIMAL" packages/nocodb/src/utils/common/NcConnectionMgrv2.ts` = 1; graph resolved `NcConnectionMgrv2.connectionKey/getSqlClient/stashDbMajorVersion` line-exact (:46/:185/:106).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "NcConnectionMgrv2 connectionKey getSqlClient stashDbMajorVersion", limit: 10 });
```

## Verdict
Adopt composite-keyed pooled handles handed to the factory via the knex short-circuit, pool-level wire coercion, and delete-then-bump invalidation; adapt LRU size and version-stash field to host; omit Redis staleness only for single-instance hosts (keep the local delete path).
