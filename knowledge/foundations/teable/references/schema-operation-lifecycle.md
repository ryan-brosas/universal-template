<!-- capsule-v2 -->
# Schema-operation lifecycle ledger — how do you make long-running table schema changes durable, idempotent, and repairable across restarts?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How is a multi-phase DDL operation tracked so a crash mid-way leaves an auditable record that a repair pass can resume — and how do table provision states gate traffic during it?

## Provision-state + operation-ledger pairing
**Path/Symbol:** `packages/v2/core/src/application/services/TableSchemaOperationLifecycleService.ts`: `beginTableSchemaOperation` (86–95), `beginTablesSchemaOperation` (98+), fail/mark-ready helpers over shared `operationOptions` (63–77) which defaults `phase: 'metadata_pending'` and injects `tableId(s)` into the payload; state flips `application/services/TableProvisionStateService.ts:setTableProvisionState`/`setTablesProvisionState`; port contract `ports/SchemaOperationRepository.ts` (`SchemaOperationType`, `SchemaOperationPhase`, `SchemaOperationStatus`, `idempotencyKey`, `maxAttempts`, `nextRunAt`); repair consumer `application/services/TableSchemaOperationRepairHandler.ts`.
**Signature:** `beginTableSchemaOperation(unitOfWork, tableRepository, context, table, options: BeginTableSchemaOperationOptions /*{type, phase?, payload?, operationId?, idempotencyKey?, maxAttempts?, nextRunAt?}*/): Promise<Result<void, DomainError>>`.
**Data Shape:** operation row = `{operationId, idempotencyKey, operationType, phase, status, payload (always carries tableId[s]), result, lastError, maxAttempts, nextRunAt}`; table carries `provisionState: 'pending'|'ready'|'deleting'` — the two records move TOGETHER in one UoW transaction.

### Decisive source
```ts
const operationOptions = (options, payload, defaultPhase): TableProvisionOperationOptions => ({
  operationId: options.operationId,
  idempotencyKey: options.idempotencyKey,   // caller-supplied dedupe handle
  operationType: options.type,
  phase: options.phase ?? defaultPhase,     // canonical entry phase: 'metadata_pending'
  ...
});
export const beginTableSchemaOperation = async (...) =>
  setTableProvisionState(unitOfWork, tableRepository, context, table,
    options.state ?? 'pending',                              // gate traffic NOW
    operationOptions(options, tablePayload(table, options.payload), 'metadata_pending'));
```

**Flow:** begin = ONE transaction flipping provision state to `pending` AND inserting the ledger row with a canonical first phase → the DDL work proceeds (traffic can be filtered by provision state everywhere else) → completion marks ready + terminal phase; failure writes `lastError`, bumps attempt counters, and schedules retry via `nextRunAt` WITHOUT marking the table unavailable for recoverable classes (spec :137 pins this); a separate repair handler scans non-terminal rows and resumes/reconciles.
**Invariant:** the ledger row and the provision-state flip are atomic — you never get a "stuck pending" table without an audit trail explaining why; payloads are append-only by default (`marks ready and error WITHOUT replacing the initial operation payload`) so the original request stays forensically intact; idempotency keys make replays of the same logical operation converge.
**Probe:** `packages/v2/core/src/application/services/TableSchemaOperationLifecycleService.spec.ts::"begins a table operation with a canonical pending phase and table payload"` (:66), `::"marks ready and error without replacing the initial operation payload by default"` (:99), `::"records recoverable failures without marking the table unavailable"` (:137), `::"begins a multi-table operation with table IDs added to the shared payload"` (:168).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable",
  query: "beginTableSchemaOperation setTableProvisionState SchemaOperationRepository",
  limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the paired ledger+state pattern for any long-running structural change (DDL, migrations, imports): flip a gate state and write an audit row atomically, drive to terminal via attempts/nextRunAt, repair from the ledger. Adapt phases/states vocabulary and the repair scheduler to host. Omit teable's specific table-provision semantics if your resource model differs. Probes verified against the spec at HEAD.
