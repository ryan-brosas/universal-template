<!-- capsule-v2 -->
# Conditional ALTER with execute-time guard — how does an update visitor emit SQL whose actual execution depends on introspecting the live column?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How do you keep generated DDL honest when the statement should no-op if the column already has the target type?

## buildLookupConversionStatements (TableSchemaUpdateVisitor :575–628)
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/visitors/TableSchemaUpdateVisitor.ts` — `buildLookupConversionStatements` (:575–628); same pattern in `createForeignKeyConstraintStatement` DO-block (rules/helpers/StatementBuilders.ts :113–190) and guarded index creation (:318–341).
**Signature:** statement = `{scope:'data', compile(executorProvider), execute({scopedDb})}` — compile embeds a best-effort ALTER; execute re-introspects and only then runs it.
**Data Shape:** expected PG type string derived from domain column type with a dialect alias map (`timestamptz` ⇒ `'timestamp with time zone'` for information_schema comparison).

### Decisive source
```ts
execute: async ({ scopedDb }) => {
  const introspector = new PostgresSchemaIntrospector(scopedDb);
  const currentColumnResult = await introspector.getColumn(schema, tableName, dbFieldName);
  if (currentColumnResult.isErr()) throw new Error(currentColumnResult.error.message);
  const currentColumn = currentColumnResult.value;
  if (!currentColumn) throw new Error(`Lookup column not found: ${dbFieldName}`);
  if (currentColumn.dataType === expectedDataType) return;   // ← the conditional no-op
  await scopedDb.executeQuery(compileAlter(scopedDb));
},
```

**Flow:** lookup-fieldId change where cellValueType flips (e.g. text→number inner field) emits this guarded statement; compile() produces a valid NULL-fill ALTER for logging/preview/dry-run paths; execution path introspects FIRST so idempotent replays (retry after partial failure, repair runs) never rewrite data unnecessarily.
**Invariant:** compile must remain semantically valid WITHOUT db access (DummyDriver tests); the guard compares information_schema dataType STRINGS, requiring the alias normalization step — comparing raw 'timestamptz' against 'timestamp with time zone' would always mismatch and cause perpetual rewrites.
**Probe:** graph probe search_graph 'buildLookupConversionStatements'; source pin TableSchemaUpdateVisitor.ts :601–622; covered indirectly by LookupColumnType.pglite.spec matrix.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildLookupConversionStatements expectedDataType PostgresSchemaIntrospector getColumn", limit: 10 });
```

## Verdict
Adopt compile-valid/execute-guarded statements for any DDL that may already be applied; adapt the alias map to host dialect; omit when your migration framework already dedupes applied DDL.
