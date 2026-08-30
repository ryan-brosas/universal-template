<!-- capsule-v2 -->
# Meta touch monotonic clock — how does table_meta.last_modified_time double as an ordering-safe cache key?

## GREATEST(now, prev + 1ms) CASE expression ⇒ strictly increasing even within one millisecond
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `touchTableMeta(context, tableId, actorId)` (:3335–3355, SQL :3347–3350), `resolveMetaDb` (:3357–3360, scope inference `this.db === this.metaDb ? 'data' : 'meta'`); call sites after every successful mutation (:1333/:1740/:2214/:2453/:2861/:3262). Companion capsule: `query-version-touch-algebra`.
**Signature:** `touchTableMeta(...): Promise<void>` (void — best-effort).

### Decisive source
```sql
last_modified_time = CASE
  WHEN "last_modified_time" IS NULL THEN CURRENT_TIMESTAMP
  ELSE GREATEST(CURRENT_TIMESTAMP, "last_modified_time" + interval '1 millisecond')
END
-- Ensure monotonic millisecond progression for cache-key invalidation.
```

**Flow:** after each mutation commits its DML (still inside the tx), bump the meta row's timestamp with the monotonic CASE, stamp the acting user, on the scope-resolved meta connection.
**Invariant:** Wall-clock CURRENT_TIMESTAMP is NOT monotonic under NTP or same-ms bursts; clients use this timestamp as an invalidation/version token, so equal-or-lower values would drop legitimate refreshes. `prev + 1ms` forces strict increase; GREATEST keeps real forward time winning across nodes. resolveMetaDb infers scope by IDENTITY of the two injected connections (`db === metaDb` means single-db mode → tag 'data') — porters hard-coding 'meta' break embedded/single-db deployments. Failure of the touch itself propagates as a thrown error inside the caller's try (it runs before `finish()` in updateOne but after computed in insert) — acceptable because a failed touch should abort the whole write rather than emit untracked mutations.
**Probe:** deterministic grep :3347–3350; behavior pinned indirectly via update suites asserting meta rows.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "touchTableMeta last_modified_time GREATEST interval", limit: 5 });
```
## Verdict
Adopt whenever a metadata timestamp feeds client caches: SQL-side GREATEST(now, prev+ε) beats application-side Date.now() for multi-writer safety.
