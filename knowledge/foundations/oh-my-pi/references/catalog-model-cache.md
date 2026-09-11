<!-- capsule-v2 -->
# SQLite model cache — how do you cache provider catalogs cross-process without persisting credentials or resurrecting stale schemas?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** What does a durable, corruption-healing, secret-free model catalog cache look like?

## Versioned rows + header-omission ledgers + quarantine-and-reopen healing
**Path/Symbol:** `packages/catalog/src/model-cache.ts:CACHE_SCHEMA_VERSION` (:26), `openDb` (:52), `quarantineCorruptModelCache` (:130), `healCorruptModelCache` (:151), `migrateCacheSchema` (:191), `readModelCache` (:210), `toCachedModelSpec` (:293), `writeModelCache` (:309).
**Signature:** `readModelCache(providerId, ttlMs, now, dbPath?): CacheEntry | null`; `writeModelCache(providerId, updatedAt, models, authoritative, staticFingerprint, dbPath?, staticHeaderSources?, restorableHeaderFallback?)`.
**Data Shape:** one row per provider: `{provider_id PK, version, updated_at, authoritative, static_fingerprint, header_omitted_model_ids JSON, unrestorable_header_model_ids JSON, header_restore_version, models JSON}` — models persist sparse `compatConfig`, never the resolved record.

### Decisive source
```ts
// Install the busy handler BEFORE any lock-taking statement (#2421).
db.run("PRAGMA busy_timeout = 3000");
// Schema invalidation can delete rows containing credentials written by old
// versions. Overwrite deleted cells instead of leaving their bytes in free
// pages where a raw scan of models.db can still recover them (#5780).
db.run("PRAGMA secure_delete = ON");

// Headers are NEVER persisted: custom/runtime providers may use arbitrary
// credential header names, so no name-based filter can be complete.
const { headers: _h, compatConfig, supportsComputerUseConfig, ...rest } = model;
return { ...rest, supportsComputerUse: supportsComputerUseConfig, compat: compatConfig };

// The legacy `UPDATE ... WHERE version = 2` migration silently promoted the
// first cache version to the current one, defeating EVERY subsequent
// invalidation (#4146). Delete instead:
db.run("DELETE FROM model_cache WHERE version <> ?", [CACHE_SCHEMA_VERSION]);
```

**Flow:** open shared (or per-path) DB with pragmas → read validates `version === CACHE_SCHEMA_VERSION` else null → TTL freshness computed against injected clock (`ageMs >= 0` guards clock skew) → write projects live models through `toCachedModelSpec`, recording which ids had headers and whether those headers matched a static source or the trusted provider-wide fallback → on `isSqliteCorruptionError`: close handle, rename db+wal+shm to `.corrupt-<ts>`, log once at error then debug for repeat heals of the same path (dying-disk spam guard), retry once → all cache writes best-effort (failures never break resolution).
**Invariant:** (1) no credential value ever touches disk — restorability is decided AT WRITE TIME and recorded as id lists; (2) schema migration must delete, never update-in-place across versions; (3) corrupt files are quarantined by RENAME (sidecar-tolerant) so the next open recreates instead of re-querying broken bytes forever (#8867); (4) synthesized `-fast`/`-1m` variants match static headers via `requestModelId` too (#6037/#6284).
**Probe:** direct `packages/catalog/test/build.test.ts:851` (sparse-spec round trip), `:1196/:1231/:1268/:1310/:1347` (header restore ladder incl. legacy request-model recovery), `:944` (schema-version invalidation), `test/provider-cache-id.test.ts:7` (cache namespace resolution).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "readModelCache writeModelCache secure_delete model cache sqlite", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the versioned-row invalidation-by-delete, header-omission ledger design, PRAGMA trio, and rename-quarantine healing; adapt row contents to your catalog shape; omit `static_fingerprint` if you have no static+dynamic merge. Coverage caveat: none — heavy direct coverage via tmpdir SQLite fixtures.
