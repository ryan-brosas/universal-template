<!-- capsule-v2 -->
# generated-column-immutability-contract — What may a generated-column formula emitter do that the SELECT emitter may not (and vice versa)?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Which functions are banned from STORED generated columns and how does the validator + emitter enforce immutability?

## All SQL must be immutable: no subqueries, no NOW(), NULL-fallback casts; validator vetoes whole families pre-DDL
**Path/Symbol:** `apps/nestjs-backend/src/db-provider/generated-column-query/postgres/generated-column-query.postgres.ts` header contract (:17-19), `castToTimestamp` (:1594-1626, NULL::timestamp fallbacks :1607/:1616), baked date-like guard in looseNumericCoercion (:154-175), `countAll` jsonb_array_length (:1429); gate-keeper `features/record/query-builder/formula-support-generated-column-validator.ts:validateFormula` (:40-86) + field-reference veto (:126-166).
**Signature:** `class GeneratedColumnQueryPostgres extends GeneratedColumnQueryAbstract`; `validateFormula(expression: string): boolean`.
**Data Shape:** same coercion helpers as the SELECT side but with stricter bodies (no COLLATE opts indirection; date-like rejection BAKED IN rather than optional).

### Decisive source
```ts
// class doc:
// Converts Teable formula functions to PostgreSQL SQL expressions suitable
// for use in generated columns. All generated SQL must be immutable.
...
// castToTimestamp — non-datetime inputs can never parse:
if (!looksDatetime && !isTimestampish(date)) return 'NULL::timestamp';
if (paramInfo?.hasMetadata && paramInfo.type === 'number') return 'NULL::timestamp';
```
Validator vetoes (return false): references to Link/Rollup/ConditionalRollup/lookup/CreatedTime/LastModifiedTime/AutoNumber/CreatedBy/LastModifiedBy fields; nested formulas not themselves persisted as generated columns; datetime-string concatenation; datetime text slicing; logical fns with non-boolean args; numeric fns with non-numeric args; any fn unsupported by the provider's supportValidator.

**Flow:** field DDL request → AST walk with visited-set recursion through nested formulas → family vetoes → per-function support check against the generated-column provider → only then is STORED DDL emitted with immutable-only SQL (guards return typed NULL instead of calling volatile functions).
**Invariant:** the SELECT compiler may emit mutable/subquery SQL freely (see its error() using pg_advisory_unlock_all WHERE FALSE); the generated-column twin must keep every output deterministic. The validator runs BEFORE DDL so an unsupported formula degrades to a non-persisted computed field, never to a broken column.
**Probe:** upstream direct spec `formula-support-generated-column-validator.spec.ts` (rejects numeric-on-text args, allows numeric pair, rejects TEXTBEFORE/TEXTSPLIT); static byte-exact: `grep -n "NULL::timestamp" generated-column-query.postgres.ts` → :1607/:1616.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"FormulaSupportGeneratedColumnValidator","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the twin-provider split with an explicit immutability contract and pre-DDL validator. Adapt veto families. Omit nothing.
