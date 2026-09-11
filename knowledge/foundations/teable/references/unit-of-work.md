<!-- capsule-v2 -->
# Dual-database Unit of Work — how do you run meta and data writes atomically when they live in two different Postgres databases?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How is a transaction scope bound into an ambient execution context, reused across sibling scopes on one physical DB, and made retryable for deadlocks — while keeping afterCommit handlers exact-once?

## Ambient scoped transactions with sibling reuse + abort-carrier retries
**Path/Symbol:** `packages/v2/adapter-db-postgres-shared/src/unitOfWork.ts`: `PostgresUnitOfWorkTransaction` (60+, state machine `'pending'|'committing'|'committed'|'rollingBack'|'rolledBack'`, afterCommit/afterRollback handler queues), retry gate `shouldRetryTransactionAbort` (48–52) over `isRetryableTransactionAbort` (365–373), abort carrier `class UnitOfWorkAbort` (23–26); core helpers `packages/v2/core/src/ports/ExecutionContext.ts`: `getUnitOfWorkTransaction` (:47), `activateUnitOfWorkScope` / `bindUnitOfWorkTransaction` / `registerAfterCommit` (:178–188) / `registerAfterRollback` (:190–200) / `withoutTransaction` (:202+); runner `runInTransaction` used by every adapter.
**Signature:** `registerAfterCommit(context, handler): boolean` (false = no transaction ⇒ caller must run inline); retry predicate `(error: DomainError, attempt, maxRetries) => attempt < maxRetries && isRetryableTransactionAbort(error)`.
**Data Shape:** context carries per-scope (`meta` vs `data`) transaction slots; a scope binds either its own Kysely `Transaction` or REUSES the sibling scope's when both tokens point at the same physical database; handlers are queued with an explicit state machine so late registration can't double-fire.

### Decisive source
```ts
const isRetryableTransactionAbort = (error: DomainError): boolean => {
  if (!error.tags.includes('infrastructure')) return false;   // tag-gated, not string-only
  const message = error.message.toLowerCase();
  return (
    message.includes('deadlock detected') ||
    message.includes('could not serialize access') ||
    message.includes('serialization failure')
  );
};

afterCommit(handler) {
  if (this.state === 'committed') { void handler(); return; }  // already committed: run now
  if (this.state === 'rollingBack' || this.state === 'rolledBack') return; // never after rollback
  this.afterCommitHandlers.push(handler);
}
```

**Flow:** application code opens work via the UoW port → the postgres adapter resolves which physical DB each scope hits → same DB ⇒ ONE transaction shared by both scopes (schema-qualified tables keep them logically separate); different DBs ⇒ two independent transactions (cross-DB consistency is the app's saga concern, not pretended 2PC) → repositories resolve their handle with `resolvePostgresDbOrTx(db, context)` so every query in the flow lands in the ambient tx → domain errors thrown as `UnitOfWorkAbort` roll back, get classified by the tag+message retry gate, and the whole operation re-runs bounded times → afterCommit handlers fire exactly once, post-commit, including ones registered DURING commit.
**Invariant:** afterCommit runs only after durable success and exactly once (late-registration during commit still executes; anything registered after rollback never runs); registerAfterCommit returning FALSE means "no ambient tx — execute inline or schedule yourself"; retries wrap the ENTIRE unit of work because partial side effects outside the DB cannot be un-done; deadlock detection is tag-first so unrelated 'infrastructure' errors don't spin.
**Probe:** `packages/v2/adapter-repository-postgres/src/unitOfWork.shared.spec.ts::"runs afterCommit handlers registered after the transaction has committed"` (:17), `::"reuses a sibling scope transaction when meta and data share the same physical database"` (:86), `::"keeps meta and data scopes separate when they use different databases"` (:149), `::"does not reuse a sibling transaction when the same database uses different schemas"` (:174).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable",
  query: "PostgresUnitOfWorkTransaction registerAfterCommit runInTransaction",
  limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ambient scope-bound transactions with sibling reuse (kills self-deadlock when meta+data share a DB) and the state-machine afterCommit queue; adopt tag-gated deadlock retry around whole units of work. Adapt scope names, retry budgets, and cross-DB sagas to host. Omit teable's specific meta/data split if your storage is single-DB. Probes verified against unitOfWork.shared.spec at HEAD.
