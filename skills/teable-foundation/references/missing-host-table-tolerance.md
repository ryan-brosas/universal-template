<!-- capsule-v2 -->
# Missing-host-table tolerance — why does record deletion treat a vanished junction/FK host table as a warning instead of an error?

## preflight information_schema check + recursive 42P01 classifier → warn-and-continue in BOTH load and cleanup phases
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `resolveExternalLinkHostPlan(field)` (:4189–4208: manyMany|oneMany-oneWay⇒junction-delete, oneMany⇒fk-nullify, else none), `checkTableExists` (:4210–4222), `isMissingRelationError(error)` (:4224–4251, recursion through `.cause`/`.originalError`, code '42P01' or message contains relation+does not exist), `warnMissingLinkHostTable` (:4253–4274), preflight gate (:4276–4313) consumed by `executeOutgoingLinkDeleteOp` (:4319–4380, catch-tolerance :4362–4373) and `loadExistingLinkRecordIdsBatch` (:4387–4523, catch-tolerance :4501–4516). Tests: delete.spec.ts 'tolerates missing junction host table during delete and keeps warning logs' (:807), 'tolerates missing foreign host table during delete…' (:903).
**Signature:** `(field): Result<ExternalLinkHostPlan | undefined>`; tolerance helpers return ok(...) with empty data.

### Decisive source
```ts
if (isMissingRelationError(error)) {
  warnMissingLinkHostTable(logger, { phase: 'cleanup-outgoing', field, hostTableName: operation.tableName, ... });
  return ok(undefined);                       // swallow ONLY this error class
}
return err(domainError.infrastructure({ message: `Failed to clean outgoing link records: …` }));
```
```ts
return isMissingRelationError(candidate.cause) || isMissingRelationError(candidate.originalError);
```

**Flow:** before any cross-table statement, probe information_schema for the host table (cheap, no error path) → if absent, log a structured warning and skip the phase → if present but the statement STILL fails, classify the thrown error: SQLSTATE 42P01 (direct or nested in driver wrappers via cause/originalError recursion) means missing-relation ⇒ same warn-and-ok; anything else propagates as infrastructure DomainError.
**Invariant:** This exists because base/table deletion races leave link metadata momentarily pointing at dropped tables — a hard failure would make RECORDS UNDELETABLE (worse than stale link bookkeeping). The double defense matters: preflight avoids the error in the common case, but the catch-classifier is still required because DDL can drop between check and statement. The classifier must recurse wrapped errors (kysely/pg nest causes) — porters checking only `error.code` misclassify driver-wrapped 42P01s as hard failures. Only THIS class is swallowed; constraint violations etc. still abort.
**Probe:** delete.spec.ts :807/:903 pin both phases' tolerate-and-log behavior.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "isMissingRelationError preflightExternalLinkHostTable executeOutgoingLinkDeleteOp", limit: 8 });
```
## Verdict
Adopt wherever metadata-driven cross-table writes can outlive their targets: two-layer tolerance (pre-probe + classified catch) keeps destructive flows resilient while preserving real errors.
