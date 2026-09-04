<!-- capsule-v2 -->
# Query-ops repositories — how does teable persist observations, recommendations, and remediation tasks with upserts, lease claims, and Result rails?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** The query-ops meta tables need idempotent writes (observation window accumulation, open-recommendation upsert, task upsert), a concurrency-safe task claim, and a lease acquire. What SQL patterns make each correct?

## Observation accumulate / open-recommendation upsert / task claim / lease acquire
**Path/Symbol:** `packages/v2/adapter-table-query-ops-postgres/src/repositories.ts` — `PostgresTableQueryObservationRepository.record` (24–73) + `.findRecent` (75–100), `PostgresTableQueryRecommendationRepository.save` (189–243) + `.findOpenByShape` (153–170), `PostgresTableQueryRemediationTaskRepository.claimNextAccepted` (310–343) + `.save` (266–308), `PostgresTableQueryOpsLeaseRepository.acquire` (349–375); `rowToObservation`/`rowToRecommendation`/`rowToTask` (378–462).
**Signature:** all return `Promise<Result<T, DomainError>>`; `record(observation)`; `save(recommendation)`; `claimNextAccepted({workerId, now, allowedKinds})`; `acquire({leaseKey, ownerId, ttlMs, now})`.

### Decisive source
```ts
// observation: id = `${tableId}:${queryKind}:${shapeHash}:${windowStart.toISOString()}`,
// ON CONFLICT (table_id, query_kind, shape_hash, window_start) DO UPDATE — additive counters:
request_count = table_query_observation_window.request_count + excluded.request_count,
max_duration_ms = greatest(table_query_observation_window.max_duration_ms, excluded.max_duration_ms),
sql_diagnostics = coalesce(excluded.sql_diagnostics, table_query_observation_window.sql_diagnostics)
// recommendation: open rows upsert on (table_id, shape_hash, policy_version) WHERE status='open';
// non-open rows upsert on id:
.onConflict(oc => oc.columns(['table_id','shape_hash','policy_version']).where('status','=','open').doUpdateSet(updateValues))
// task claim — atomic, one row, FOR UPDATE SKIP LOCKED inside a subselect:
UPDATE table_query_remediation_task SET locked_by=${workerId}, locked_at=${now}, last_modified_time=${now}
WHERE id = (SELECT id FROM table_query_remediation_task
  WHERE status='queued' AND kind = ANY(${allowedKinds}) AND attempts < max_attempts
    AND (locked_at IS NULL OR locked_at < ${now - 60_000})   -- stale reclaim after 60s
  ORDER BY created_time ASC FOR UPDATE SKIP LOCKED LIMIT 1)
RETURNING *
// lease acquire — renew-if-expired-or-owner:
INSERT INTO table_query_ops_lease (lease_key, owner_id, expires_at, updated_time) VALUES (...)
ON CONFLICT (lease_key) DO UPDATE SET owner_id=excluded.owner_id, expires_at=excluded.expires_at, updated_time=excluded.updated_time
WHERE table_query_ops_lease.expires_at <= ${now} OR table_query_ops_lease.owner_id = ${ownerId}
RETURNING lease_key
```

**Flow:** `record` computes a deterministic id and accumulates counters on conflict (sums, `greatest` for max, `coalesce` for diagnostics); `findRecent` reads newest-first with optional table filter; `save` upserts open recommendations by the open-unique key (partial index `WHERE status='open'`) or by id for non-open; `claimNextAccepted` atomically claims the oldest eligible queued task with `FOR UPDATE SKIP LOCKED`, skipping ones locked <60s ago; `acquire` inserts-or-renews a lease only when expired or owned by the caller.
**Invariant:** observation windows are additive (never overwrite counts), max is `greatest`; open recommendations are unique per (table, shape, policy) via a partial unique index; task claims are single-statement and `SKIP LOCKED` so concurrent workers never double-claim; lease renewal is owner-or-expiry gated so a foreign holder is never stolen mid-lease.
**Probe:** `repositories.spec.ts:49` 'upserts open recommendations by table, shape, and policy' (recommendation save); observation/task/lease paths are DB-backed and exercised via the advisor integration specs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresTableQueryObservationRepository record PostgresTableQueryRemediationTaskRepository claimNextAccepted PostgresTableQueryOpsLeaseRepository acquire", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the additive observation upsert, open-partial-unique recommendation upsert, `FOR UPDATE SKIP LOCKED` task claim with stale-reclaim, and owner-or-expiry lease renewal; adapt table/column names and TTLs to host; omit teable's shape/snapshot domain objects if the host stores raw JSON. Coverage caveat: `repositories.ts` is parse_partial at :119 and :360 (template-literal lines in the claim/lease SQL); the surrounding logic is indexed.
