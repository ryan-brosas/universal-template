<!-- capsule-v2 -->
# Idempotency-key operation ledger — how does a single table drive upsert/advance/claim/retry for long-running schema work?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How are DDL-ish operations persisted so retries, claims, and manual interventions all key off one idempotency key?

## ON CONFLICT upsert with SQL-side attempt counting + stale-claim CTE
**Path/Symbol:** `packages/v2/adapter-repository-postgres/src/repositories/PostgresSchemaOperationRepository.ts` (509L): `upsert` (:126-212), `advance` (:215-268), `claimNextRunnable` (:271-332), `manualRetry` (:401-447), `markDead` (:450-495), `selectorWhere` (:88-103: id XOR idempotencyKey REQUIRED), `clampLimit` (:73-76: default 100, max 500).
**Signature:** `claimNextRunnable(context, {types?, now?, staleRunningBefore? (=now-5min), lockedBy, phase?})`.
**Data Shape:** row carries `attempts/max_attempts(default 8)/next_run_at/locked_at/locked_by`; statuses pending|running|error|dead|ready.

### Decisive source
```sql
-- attempts increment INSIDE the conflict clause — no read-modify-write race
"attempts" = CASE WHEN EXCLUDED."status" IN ('error','dead')
                  THEN "schema_operation"."attempts" + 1 ELSE "schema_operation"."attempts" END,
"payload" = COALESCE(EXCLUDED."payload", "schema_operation"."payload"),   -- null = keep existing

WITH candidate AS (
  SELECT "id" FROM "schema_operation"
  WHERE ("status"='error'   AND "next_run_at" <= $now)                          -- retry due
     OR ("status"='pending' AND "next_run_at" <= $now
                           AND "last_modified_time" <= $staleRunningBefore)      -- never-started cleanup
     OR ("status"='running' AND "locked_at" IS NOT NULL AND "locked_at" <= $staleRunningBefore)  -- crashed worker
  ORDER BY "next_run_at","created_time" LIMIT 1 FOR UPDATE SKIP LOCKED
) UPDATE … SET status='running', locked_at=$now, locked_by=$who FROM candidate WHERE id=candidate.id
```

**Flow:** upsert (insert-or-overwrite by idempotency_key; error/dead bumps attempts in-SQL) → worker claims via the three-branch CTE → advance sets status/phase, clears lock unless still running → manualRetry forces status back to 'error' with next_run_at=now (optionally zeroing attempts); markDead pins 'dead' with a reason as last_error.
**Invariant:** Attempt counting lives in the UPDATE statement, never application code — concurrent upserts cannot lose increments. Claim candidates include ERROR rows whose next_run_at is due (retry scheduling is just a timestamp) and RUNNING rows past the stale deadline (crash recovery); SKIP LOCKED makes multi-worker claims disjoint. Selector requires exactly one of id/idempotencyKey — bulk-by-target mutations must go through findOpenByTarget first.
**Probe:** `PostgresSchemaOperationRepository.spec.ts:49` "claims due operations by supported type and releases the lock when advanced"; :116 "lists operations and supports manual retry and mark-dead controls".
**Coverage caveat:** none for claim/retry semantics; the stale-running branch is exercised indirectly via fixture timestamps.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresSchemaOperationRepository claimNextRunnable upsert ON CONFLICT", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt SQL-side attempt accounting + the three-branch stale-claim CTE verbatim; adapt status vocabulary; note this is the META-plane twin of query-ops-repositories' tqops_ task claim — same pattern, separate ledgers.
