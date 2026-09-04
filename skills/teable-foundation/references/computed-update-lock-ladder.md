<!-- capsule-v2 -->
# Computed advisory lock ladder — how do you serialize concurrent recomputes of the same rows without deadlocking or over-locking?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** When a recompute plan touches N seed records, how does the worker choose between per-record, batch-shard, and whole-table advisory locks — and why is the key shaped that way?

## buildComputedUpdateLockPlan + try-advisory queries
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/ComputedUpdateLock.ts` — `buildComputedUpdateLockPlan` (:77–195), lock keys (:251–257), `buildAdvisoryLockQuery`/`buildTryAdvisoryLockQuery` (:202–211), `resolveBatchShard` FNV-1a (:313–320), `isComputedUpdateLockUnavailable` (:213–214); config defaults :11–15 (maxRecordLocks 50, batchShardCount 64).
**Signature:** `buildComputedUpdateLockPlan(plan: {baseId, seedTableId, seedRecordIds, extraSeedRecords}, config): ComputedUpdateLockPlan` where the plan carries `summary.mode: 'disabled'|'none'|'record'|'batch'|'table'|'mixed'`, per-scope lock lists, and ready-to-run `statements[]`.
**Data Shape:** Lock key grammar `v2:computed:<tableId>[:batch:<shard>]`; statement = `{scope, tableId, recordId?, batchId?, key, sql, parameters}`.

### Decisive source
```sql
select pg_try_advisory_xact_lock(
  ('x' || substr(md5($1), 1, 16))::bit(64)::bigint
) as locked
-- The trailing constant column splits pg_stat_statements/queryid fingerprints per
-- lock scope: queryid ignores comments and constant VALUES, but jumbles constant
-- TYPES and target arity. Outbox locks carry their own scope column so they never
-- share this queryid; computed try-locks use the single-column shape.
```
```ts
// Table IDs are globally unique. Root-base prefixes let cross-base cascades acquire
// DIFFERENT advisory locks for the same physical target row, so PostgreSQL row-lock
// waits can consume the entire statement timeout. Key locks only by the records they protect.
const buildRecordLockKey = (tableId, recordId) => `v2:computed:${tableId}:${recordId}`;
```

**Flow:** dedupe seed groups per table → if group ≤ maxRecordLocks take RECORD locks; else if batchShardCount > 0 shard record ids by FNV-1a hash mod 64 into BATCH locks (padded shard ids keep key ordering stable); else TABLE lock → statements sorted by key (deterministic acquisition order prevents lock-order deadlock) → all executed as `pg_advisory_xact_lock` inside the task transaction so they release at commit/rollback. Any try-miss surfaces as `computed_update.lock_unavailable`, which the worker treats as control-flow requeue (never an error, never attempt-consuming).
**Invariant:** Keys must NOT embed base/space prefixes even though table ids are globally unique — the comment documents that cross-base cascades then map to different locks for the same physical row and Postgres row-lock waits eat the whole statement timeout. Acquisition MUST be in sorted-key order across all scopes. Locks are xact-scoped by construction (no unlock path exists to get wrong).
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/__tests__/ComputedUpdateLock.spec.ts` (`describe('ComputedUpdateLock')` :22 pins mode selection, shard distribution, and statement shapes).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildComputedUpdateLockPlan resolveBatchShard buildTryAdvisoryLockQuery", limit: 10 });
```

## Verdict
Adopt the record→batch-shard→table escalation with sorted deterministic acquisition, md5→bit(64) advisory keys keyed ONLY by protected identity, and queryid-fingerprint discipline for attributable lock waits; adapt the key namespace and shard counts to host; omit the summary/reason telemetry fields if unneeded.
