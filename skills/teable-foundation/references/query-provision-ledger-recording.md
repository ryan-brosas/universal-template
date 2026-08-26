<!-- capsule-v2 -->
# Provision-state ledger recording — how does a bulk provision-state UPDATE leave one idempotent operation row per table?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** When N tables flip provision state together, how do their audit rows get deterministic idempotency keys and status mapping?

## Per-table derived keys + state→status mapping + COALESCE upsert reuse
**Path/Symbol:** `packages/v2/adapter-repository-postgres/src/repositories/PostgresTableRepository.ts`: `setProvisionStateMany` (:1284-1319), `recordSchemaOperations` (:1321-1414), `tableProvisionStateToOperationStatus` (:82-88: ready→ready, error→error, else pending), key derivation (:1342-1346: `tables.length===1 && operation?.idempotencyKey ? given : `${operationId}:table:${tableId}``).
**Signature:** `setProvisionStateMany(context, tables, state, operation?): Promise<Result<void, DomainError>>`; operationId defaults to `context.requestId ?? operationType`.
**Data Shape:** attempts seeded 1 only when status='error'; maxAttempts default 8; the INSERT…ON CONFLICT clause is byte-identical to PostgresSchemaOperationRepository.upsert (COALESCE payload/result, error-status attempt bump).

### Decisive source
```ts
const operationId = operation?.operationId ?? context.requestId ?? operationType;
const idempotencyKey =
  tables.length === 1 && operation?.idempotencyKey
    ? operation.idempotencyKey                          // single-table callers keep full control
    : `${operationId}:table:${tableId}`;                // bulk: deterministic per-table keys
```

**Flow:** single UPDATE flips provision_state for all table ids → for each table, an upsert into schema_operation records type/phase/status with the derived key → re-running the same request (same requestId) lands on the SAME row via ON CONFLICT and refreshes it instead of duplicating.
**Invariant:** Bulk operations MUST NOT share one idempotency key (the second table's upsert would overwrite the first's row) — hence the length-1 escape hatch for explicit caller keys. The repository owns ledger-writing so no service layer can flip state without an audit trail; the SQL-side attempts CASE keeps counting race-free (see query-schema-operation-ledger).
**Probe:** covered indirectly via `PostgresTableRepository.spec.ts` provision suites + schema-operation repo spec :49/:116; parse_partial flag = line 1224.
**Coverage caveat:** the bulk-key-derivation branch verified by source reading; direct spec pins the single-table path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "recordSchemaOperations setProvisionStateMany tableProvisionStateToOperationStatus", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt per-entity derived idempotency keys for bulk ledgers; adapt key grammar; keep the state→status mapping total (unknown states map to pending, never throw).
