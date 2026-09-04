<!-- capsule-v2 -->
# Table CTE insert — how do table+fields+views land atomically in one statement while the aggregate stays authoritative?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does PostgresTableRepository.insert persist three tables in one round trip and derive db names without trusting callers?

## data-modifying CTE chain + max(order) subquery + post-commit meta backfill
**Path/Symbol:** `packages/v2/adapter-repository-postgres/src/repositories/PostgresTableRepository.ts`: `insert` (:110-414: order subquery :122-128, dbTableName collision check :138-150, CTE assembly :365-390), `insertMany` (:417-580: per-base order watermark + offset, META_INSERT_BATCH_SIZE=500 chunked inserts), ambient-tx fork (:396-398: `transaction ? persist(transaction) : this.db.transaction().execute(...)`).
**Signature:** `insert(context, table): Promise<Result<Table, DomainError>>`; `joinDbTableName(baseId, tableId)` from ../naming composes the physical name when domain lacks one.
**Data Shape:** view rows serialize query as `{filter?, sort:{sortObjs,manualSort?}?, group?}` JSON strings; field rows built by TableFieldPersistenceBuilder from db-meta; `applyDbMeta` writes resolved dbTableName/dbFieldName BACK onto the domain aggregate after commit.

### Decisive source
```sql
with table_insert as (
  insert into "table_meta" (…) values (…, (select coalesce(max("order"),0)+1 from table_meta where base_id=$1), …)
)
, field_insert as ( insert into "field" … )     -- omitted entirely when zero rows
, view_insert  as ( insert into "view"  … )
select 1
```
```ts
const transaction = getPostgresTransaction<V1TeableDatabase>(context, 'meta');
const persistResult = transaction
  ? await persist(transaction)                                  // join AMBIENT unit of work
  : await this.db.transaction().execute(async (trx) => persist(trx));   // own tx otherwise
```

**Flow:** compute order via MAX subquery → derive/join db_table_name (existing value collision-checked against table_meta) → build all row sets in memory → ONE statement with conditional CTE members executes inside the ambient meta transaction when present → after success, applyDbMeta rehydrates physical names onto the domain objects (repository is the only place that knows them). insertMany trades the CTE for per-base watermarks + batched builder inserts to avoid parameter blowup.
**Invariant:** Physical naming authority flows DB-ward from the domain but never the reverse mid-write: collisions fail loudly BEFORE any insert. Empty child collections omit their CTE branch rather than emitting empty VALUES (syntax error in PG). The dual fork means every repository method participates correctly whether or not a unit-of-work scope is active.
**Probe:** `PostgresTableRepository.spec.ts` + `PostgresTableRepository.helpers.spec.ts` cover insert/mapping; parse_partial flag = line 1224 only.
**Coverage caveat:** direct spec coverage exists for insert paths; the CTE-vs-batch asymmetry between insert and insertMany is source-read only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresTableRepository insert joinDbTableName applyDbMeta", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the conditional-CTE atomic insert and ambient-tx fork; adapt naming rules; keep post-commit meta backfill — hiding db names from the domain until persistence succeeds prevents phantom-name leaks on failure.
