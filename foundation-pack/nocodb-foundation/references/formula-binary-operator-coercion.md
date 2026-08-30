<!-- capsule-v2 -->
|# formula binary operator coercion — how does a JS-style formula operator (+, ==, /, <) become correct SQL per dialect without runtime type errors?

**Source:** nocodb (Sustainable Use License) `develop@f7513664f3f3b7286023a7e832a8333808f7557b`; Codebase Memory `nocodb`. **Question:** Where do formula operators get rewritten before any SQL exists, and which per-dialect coercions keep mixed-type expressions from 500ing the list?

## formula binary operator coercion
**Path/Symbol:** `packages/nocodb/src/db/formulav2/parsed-tree-builder.ts:binaryExpressionBuilder` (:333–725).
**Signature:** `binaryExpressionBuilder({context, pt: BinaryExpressionNode, fn, prevBinaryOp, knex, columnIdToUidt, aliasToColumn, model}): Promise<{ builder }>` — `fn` is the recursive dispatcher handed down from `_formulaQueryBuilder`.
**Data Shape:** MUTATES `pt.left`/`pt.right` in place, swapping operands for synthetic CallExpression nodes; returns one knex Raw built from an interpolated SQL string.

### Decisive source
```ts
// :356–368 — `&` (and string-typed `+` at :371) never emit SQL: they rewrite to CONCAT
if (pt.operator === '&') {
  return fn({ type: JSEPNode.CALL_EXP, arguments: [pt.left, pt.right],
    callee: { type: 'Identifier', name: 'CONCAT' } }, prevBinaryOp);
}
// :469–485 — division pre-casts BOTH sides to FLOAT, then materializes each
//   operand to a STRING via .toQuery() before interpolation
let left = (await fn(pt.left, pt.operator)).builder.toQuery();
let right = (await fn(pt.right, pt.operator)).builder.toQuery();
// :495–512 — ordering comparisons over mixed STRING/NUMERIC: NULL-safe numeric rescue
const toSafeNumeric = (expr: string): string => {
  switch (knex.clientType()) {
    case 'pg':        // btrim + regex guard so junk text yields NULL (else 42883)
      return `(CASE WHEN btrim((${expr})::text) ~ '^[-+]?[0-9]+(\\.[0-9]+)?$' THEN (${expr})::double precision END)`;
    case 'mssql':     return `TRY_CAST(${expr} AS FLOAT)`;
    case 'oracledb':  return `CAST(${expr} AS BINARY_DOUBLE DEFAULT NULL ON CONVERSION ERROR)`;
    default:          return expr; // mysql2/sqlite coerce implicitly — untouched
  }
};
// :659–674 — scalar comparison materialization, gated by parent context
const isMssqlScalarComparison =
  (isMssql || isOracle) &&
  ['=', '!=', '<', '>', '<=', '>='].includes(pt.operator) &&
  prevBinaryOp !== 'AND' && prevBinaryOp !== 'OR';
...
sql = isMssql || isOracle
  ? `(CASE WHEN ${sql} THEN 1 ELSE 0 END )`
  : `(CASE WHEN ${sql} THEN true ELSE false END )`;
// :706–718 — mssql arithmetic: tedious returns BIGINT/DECIMAL as JS STRINGS
if (knex.clientType() === 'mssql' && ['+', '-', '*'].includes(pt.operator) &&
    pt.dataType === FormulaDataTypes.NUMERIC) {
  sql = `CAST(${sql} AS FLOAT)`;
}
// :720–723 — THE exit: re-escape placeholders, parenthesize on precedence change
const query = knex.raw(sql.replace(/\?/g, '\\?'));
if (prevBinaryOp && pt.operator !== prevBinaryOp) { query.wrap('(', ')'); }
```

**Flow:** the builder first FOLDS operators into other tree nodes — `&` and string-typed `+` become CONCAT calls; `==`/`!=` with a BLANK() operand swap to ISBLANK/ISNOTBLANK (string side) or ISNULL/ISNOTNULL (:404–438); boolean-vs-numeric equality wraps the numeric side in a BOOLEAN() call (:386–403); mixed-dataType `==` STRING()-casts both sides (:441–466); `/` FLOAT-casts both operands and the emission phase wraps the right side in NULLIF(right, 0) for divide-by-zero (:675–700). Then both operands materialize through `.toQuery()` INTO STRINGS and the per-dialect corrections apply to the string: ordering comparisons coerce the text side through `toSafeNumeric` (NULL-producing, so non-numeric rows drop out instead of raising pg 42883); Date-column-vs-'' comparisons collapse to `IS NULL`/`IS NOT NULL` and unparseable date literals collapse to `IS NOT NULL` on pg/mssql/oracle (:529–579); `= ''`/`!= ''` expand to `IS NULL OR CAST(x AS TEXT) = ''` (oracle arm: plain `IS [NOT] NULL` because ''≡NULL and CAST AS TEXT is ORA-00902; mssql textType NVARCHAR(MAX) because T-SQL has no TEXT cast) (:618–652); sqlite CONCAT chains COALESCE both sides to ''(:582–604); mysql2 wraps the whole comparison in IFNULL(expr, <literal-empty?>) (:606–617); standalone (non-AND/OR-parented) comparisons CASE-materialize to 1/0 or true/false; finally the `\?` re-escape + conditional paren-wrap at the exit (:720–723).
**Invariant:** (1) Operand rewriting MUTATES the shared parsed tree BEFORE recursion — cloning instead of mutating loses the fnName stamps (`assignFnName` :26–33) that aggregate thunks read later. (2) The `\?` re-escape fires at EVERY materialization exit exactly once; skipping it lets literal `?` characters in string data shift all downstream bindings. (3) The prevBinaryOp gate is semantic: comparisons directly under AND/OR must stay bare predicates (they compose as WHERE clauses), standalone ones must materialize (SELECT contexts have no boolean type on mssql/oracle) — flipping this either breaks WHERE composition or leaks booleans into projections. (4) The ordering-comparison rescue MUST produce NULL (not 0/'') for non-numeric text so rows exclude silently. (5) mysql2 IFNULL-wrapping and sqlite COALESCE are deliberate dialect asymmetries in NULL propagation, not drift to unify.
**Probe:** `packages/nocodb/src/db/formulav2/parsed-tree-builder.ts` :333–725 (search_graph resolved `binaryExpressionBuilder` line-exact 333-725 at pin f7513664f3f3). Runner BLOCKED (no upstream unit tests for the db/ plane) → line-anchored deterministic check.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "binaryExpressionBuilder toSafeNumeric prevBinaryOp", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the rewrite-then-recurse operator folding, the NULL-safe per-dialect ordering rescue, the parent-context-gated CASE materialization, and the mssql FLOAT arithmetic cast; adapt cast syntaxes to host dialects; omit snowflake/databricks branches unless the host targets them.
