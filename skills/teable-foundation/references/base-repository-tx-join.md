<!-- capsule-v2 -->
# Repository transaction joining — how do repository methods participate in an ambient transaction without leaking a meta write into a data transaction?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Every Postgres repository repeats a join-or-open pattern around Result-returning persistence — what is the exact contract?

## scope-tagged tx reuse + open-if-absent + infrastructure error wrapping
**Path/Symbol:** `packages/v2/adapter-repository-postgres/src/repositories/PostgresBaseRepository.ts` — `insert` (24–74), `findOne` (76–101), `find` (103–142), `sequenceResults` (157–164), module-level `describeError` (167–179); shared helpers `getPostgresTransaction`/`resolvePostgresDbOrTx` from `@teable/v2-adapter-db-postgres-shared` (`unitOfWork.ts`, already cited by unitOfWork capsules); tests `PostgresBaseRepository.spec.ts` 'inserts a base inside a transaction…' (:40), 'reuses an existing postgres transaction when present' (:53), 'does not reuse a data-scoped transaction for base metadata inserts' (:74), 'wraps insert failures as infrastructure errors' (:97).
**Signature:** `insert(ctx, base): Promise<Result<Base, DomainError>>`; helpers keyed by `(context, scope: 'meta'|'data')`.

### Decisive source
```ts
const transaction = getPostgresTransaction<V1TeableDatabase>(context, 'meta');
const persist = async (trx) => { /* raw SQL insert incl. computed order:
  (select coalesce(max("order"),0)+1 from base where space_id = ${DEFAULT_SPACE_ID}) */ };
try {
  const persistResult = transaction
    ? await persist(transaction)                                   // JOIN ambient tx
    : await this.db.transaction().execute(async (trx) => persist(trx)); // or OPEN one
  if (persistResult.isErr()) return err(persistResult.error);
} catch (error) {
  return err(domainError.infrastructure({ message: `Failed to insert base: ${describeError(error)}` }));
}
return ok(base);
// reads use resolvePostgresDbOrTx(this.db, context, 'meta') — same scope tag, no explicit tx
// DEFAULT_SPACE_ID = 'spc00000000000000000' — v1 single-space shim
```

**Flow:** look up an ambient transaction on the execution context FILTERED BY SCOPE TAG → join it or open a fresh one → run persistence returning Result → caught exceptions become typed `infrastructure` DomainErrors via describeError's ladder (domain error passthrough → Error name:message → string → JSON → String) → reads resolve db-or-tx with the same tag so they observe uncommitted writes inside the same unit of work.
**Invariant:** SCOPE ISOLATION is the point: a `'data'`-scoped ambient transaction MUST NOT be reused for `'meta'` writes (test :74) — cross-scope joins couple commit boundaries of unrelated databases. The computed `order` subquery runs INSIDE the insert statement so concurrent base creations serialize at the DB rather than racing a client-side max().
**Probe:** `PostgresBaseRepository.spec.ts` :40/:53/:74/:97 pin join/open/scope-refusal/error-wrapping respectively.
**Coverage:** fully indexed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresBaseRepository getPostgresTransaction resolvePostgresDbOrTx sequenceResults", limit: 8 });
```

## Verdict
Adopt the scope-tagged join-or-open pattern verbatim wherever repositories share ambient transactions across bounded contexts; adapt the scope vocabulary. describeError's non-throwing serialization ladder is directly reusable.
