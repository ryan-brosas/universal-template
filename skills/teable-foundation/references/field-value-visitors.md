<!-- capsule-v2 -->
# FieldValueVisitors — the insert/delete/database/sql-literal value conversion family

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What are the four per-field-type value conversions (insert, delete, db-format, sql-literal) and what invariants do they share?

## Field value conversion visitors
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/visitors/` — `FieldInsertValueVisitor.ts` (76-390), `FieldDeleteValueVisitor.ts` (80-235), `FieldDatabaseValueVisitor.ts` (43-210), `FieldSqlLiteralVisitor.ts` (56-243).
**Signature:** each is an `IFieldVisitor<Result<T, DomainError>>`; `FieldInsertValueVisitor.create(rawValue, ctx)` → `visitX(field)` → `FieldInsertResult = { columnValues, queryExecutors }`; `FieldDeleteValueVisitor.create(ctx)` → `FieldDeleteResult = { operation: OutgoingLinkDeleteOp | null }`; `FieldDatabaseValueVisitor.create(rawValue)` → db value; `FieldSqlLiteralVisitor.create(value)` → SQL literal string.

### Decisive source
```ts
// FieldSqlLiteralVisitor NULL casts — the VALUES-clause type-inference trap
private numericLiteral(value, pgType) { return value==null ? `NULL::${pgType}` : `${value}::${pgType}`; }
private booleanLiteral(value) { return value==null ? 'NULL::boolean' : `${value}::boolean`; }
private timestampLiteral(value) { return value==null ? 'NULL::timestamptz' : `'${escapeSqlQuotes(String(value))}'::timestamptz`; }
private jsonbLiteral(value) { return value==null ? 'NULL::jsonb' : `'${escapeSqlQuotes(String(value))}'::jsonb`; }
```

**Flow:** INSERT visitor: simple fields → `{columnValues:{db:value??null}}`; JSONB fields (attachment/user/link/multipleSelect) → JSON.stringify; computed fields (formula/rollup/lookup/created*/lastModified*/autoNumber/button/conditional*) → `computedField()` = empty columnValues (never written); link fields → columnValues + deferred `queryExecutors` (junction insert / FK set / foreign-table repoint). DELETE visitor: non-link → noOp; link → `junction-delete` (manyMany/oneMany-oneWay) or `fk-nullify` (oneMany two-way) or null (manyOne/oneOne, FK dies with record). DATABASE visitor: primitives as-is, JSONB stringified, computed → null. SQL-LITERAL visitor: per-type casts with explicit NULL casts.

**Invariant:** Computed fields are NEVER written by any visitor (they return empty/null); JSONB columns are always JSON-stringified for the pg driver; the SQL-literal visitor's explicit `NULL::<type>` casts are load-bearing for VALUES-clause type inference (a bare NULL would break column typing).

**Probe:** `record/visitors/FieldInsertValueVisitor.spec.ts`, `FieldDeleteValueVisitor.spec.ts`, `FieldDatabaseValueVisitor.spec.ts`, `FieldSqlLiteralVisitor.spec.ts` — each pins the per-field-type conversion matrix.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "FieldInsertValueVisitor FieldSqlLiteralVisitor computedField jsonValueFrom", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-visitor separation and the shared computed-never-written + JSON-stringify + explicit-NULL-cast invariants. Adapt the exact pg type names. Omit nothing portable. Probes pinned to the real spec suites.
