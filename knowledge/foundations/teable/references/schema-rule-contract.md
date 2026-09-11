<!-- capsule-v2 -->
# Schema-rule kernel contract — how does one atomic DDL capability describe apply/revert/validate without exceptions or a DI container?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What is the minimal interface a portable "schema rule" must implement so checker/repairer/planner can drive it uniformly?

## ISchemaRule + scoped statement builders
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/core/ISchemaRule.ts` — `ISchemaRule`, `TableSchemaStatementBuilder` (:17–27); helpers in `rules/helpers/StatementBuilders.ts` (`dataStatement`/`metaStatement` :26–36); plane guard `rules/core/SchemaStatementAccessPolicy.ts`.
**Signature:** `interface ISchemaRule { id; description; dependencies: ReadonlyArray<string>; required: boolean; validationScope?: 'data'|'meta'; repairMode?: 'auto'|'manual'; isValid(ctx): Promise<Result<SchemaRuleValidationResult, DomainError>>; up(ctx): Result<ReadonlyArray<TableSchemaStatementBuilder>, DomainError>; down(ctx): Result<...> }`. Builder = `{ scope, compile(executorProvider), execute?(ctx: {scopedDb,dataDb,metaDb}) }`.
**Data Shape:** rule id format `<rule-type>:<fieldId>[:<qualifier>]` (`column:fldX`, `junction_index:fldX:foreign`) — ids double as dependency edges AND dedup keys. `SchemaRuleValidationResult = { valid, missing?, missingItems?, extra?, extraItems? }` where items are structured i18n messages with stable `code`s that downstream repair hints switch on. Context carries `db` + optional `metaDb` (defaults to `db` via `createSchemaRuleContext`).

### Decisive source
```ts
// every statement is tagged with its storage plane at construction time
export const dataStatement = (statement): TableSchemaStatementBuilder =>
  scopedStatement('data', statement);
export const metaStatement = (statement) => scopedStatement('meta', statement);

// idempotent-by-SQL discipline (helpers/StatementBuilders.ts)
export const dropColumnStatement = (target, columnName) => dataStatement(
  sql`alter table ${buildTableIdentifier(target)} drop column if exists ${sql.ref(columnName)} cascade`);
```

**Flow:** rule constructed per-field with parent wiring (`new NotNullConstraintRule(field, columnRule)` sets `dependencies=[parent.id]`) → `up()` returns lazy builders (nothing compiled/executed yet) → caller compiles against data or meta db by `scope` → `executeTableSchemaStatements` (shared/db.ts) optionally asserts the compiled SQL never touches relations owned by the OTHER plane (`assertSchemaStatementRelationAccess`: regex over from/join/update/into/table + to_regclass against hardcoded meta/data relation allowlists).
**Invariant:** NO exceptions cross the rule boundary — everything is `Result<T, DomainError>`; `up` uses IF NOT EXISTS / `down` uses IF EXISTS so replaying any rule is safe; a rule validates ONLY its own concern (ColumnExistsRule explicitly does not check NOT NULL/UNIQUE — those are separate child rules).
**Probe:** `packages/v2/adapter-table-repository-postgres/src/shared/db.spec.ts:149 'rejects data-scoped statements that access metadata relations'` (+ :162 user-metadata variant, :195 custom-executor variant); rule-shape pins throughout `src/schema/rules/field/SchemaRules.pglite.spec.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "ISchemaRule TableSchemaStatementBuilder dataStatement metaStatement", limit: 10 });
```

## Verdict
Adopt the three-method rule interface, string-id dependency graph, plane-tagged lazy statement builders, and Result-only error rails; adapt the relation allowlists (they enumerate teable's meta tables) and the kysely compile seam to your query builder; omit the tracer span plumbing around execution.
