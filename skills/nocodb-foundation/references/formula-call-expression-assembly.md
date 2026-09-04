<!-- capsule-v2 -->
|# formula call-expression assembly — how do formula functions become dialect-correct SQL, and which ones are rewritten before any mapping table runs?

**Source:** nocodb (Sustainable Use License) `develop@f7513664f3f3b7286023a7e832a8333808f7557b`; Codebase Memory `nocodb`. **Question:** What is the dispatch order for a CallExpression node, and why do ADD/SUM, CONCAT, and URL get special treatment ahead of the generic function mapper?

## formula call-expression assembly
**Path/Symbol:** `packages/nocodb/src/db/formulav2/parsed-tree-builder.ts:callExpressionBuilder` (:35–331).
**Signature:** `callExpressionBuilder({context, pt: CallExpressionNode, fn, prevBinaryOp, aliasToColumn, knex, model, columnIdToUidt}): Promise<{ builder }>` — same recursive `fn` dispatcher as the binary builder.
**Data Shape:** consumes jsep CallExpression nodes; returns one knex Raw; special cases REWRITE into new synthetic trees passed back through `fn` (tail recursion), never emit SQL themselves.

### Decisive source
```ts
// :57–95 — ADD/SUM fold into + chains with per-leaf COALESCE(arg, 0);
//   dataType is CARRIED so the mssql FLOAT-cast still fires downstream
case 'ADD': case 'SUM':
  if (pt.arguments.length > 1) {
    return fn({ type: JSEPNode.BINARY_EXP, operator: '+', dataType: pt.dataType,
      left:  { type: JSEPNode.CALL_EXP, callee: { type:'Identifier', name:'COALESCE' },
               arguments: [pt.arguments[0], {type:JSEPNode.LITERAL, value:0}] },
      right: { ...pt, arguments: pt.arguments.slice(1) } }, prevBinaryOp);   // fold-right
// :96–139 — CONCAT forks BEFORE the mapper: sqlite → || chains; databricks/oracle
//   route through mapFunctionName (oracle chains || with TO_CLOB() per operand —
//   generic n-ary CONCAT(a,b) returns VARCHAR2 capped at 4000/32767 → ORA-01489)
// :140–280 — URL() rewrites into CONCAT('URI::( ', REPLACE(REPLACE(uri,'(','\('),
//   ')','\)'), ' )' [, ' LABEL::( ', REPLACE-chain(label), ' )']) because the
//   frontend URI regex breaks on escaped parens adjacent to closing parens
// :296–330 — GENERIC assembler: args materialize individually, then ONE raw
const callArgs = (await Promise.all(pt.arguments.map(async (arg) => {
  let query = (await fn(arg)).builder.toQuery();
  if (calleeName === 'CONCAT') {
    if (knex.clientType() !== 'sqlite3') {
      query = await convertDateFormatForConcat(context, arg, columnIdToUidt, query, knex.clientType());
    }
    if (knex.clientType() === 'mysql2') return `IFNULL(${query}, '')`; // mysql CONCAT(NULL,…)=NULL
  }
  return query;
}))).join();
return { builder: knex.raw(`${calleeName}(${callArgs})`.replace(/\?/g, '\\?')) };
```

**Flow:** dispatch order is (1) uppercase-name switch on the callee: ADD/SUM fold right into COALESCE-guarded `+` chains preserving dataType; CONCAT branches by client (sqlite `||`, oracle/databricks into mapFunctionName for TO_CLOB chaining, everyone else falls through to the generic n-ary assembler with per-arg date-format conversion for concat contexts and mysql2 IFNULL(x,'') NULL-shielding); URL rewrites to a CONCAT of paren-escaped segments whose leading/trailing spaces are LOAD-BEARING for the frontend URI::( … ) / LABEL::( … ) regex parser (escaped parens inside content would otherwise end the match early — see in-source comment citing PR #10707); everything else goes straight to `mapFunctionName`; (2) unmapped functions hit the generic assembler: every argument builds recursively, materializes via `.toQuery()` into a string, then joins as `NAME(arg1,arg2,…)` inside a single knex.raw with `\?` re-escape. Note the deliberate shape: only the three rewrite families exist here — real per-function SQL bodies live in the function-mapping module this file delegates to (`mapFunctionName`).
**Invariant:** (1) The switch handles ONLY tree rewrites; if you port per-function SQL emission into this file you break the layering that lets mapFunctionName own dialect tables. (2) ADD/SUM must thread `pt.dataType` through the synthetic `+` node — dropping it silently regresses mssql numeric results back to tedious strings ('10' instead of 10). (3) The generic assembler joins ALREADY-materialized strings — it never nests builders — so any argument that could contain literal `?` must have been re-escaped on ITS OWN exit; the outer `.replace(/\?/g,'\\?')` covers residual placeholders exactly once. (4) URL()'s space padding is contract with the nc-gui regex, not cosmetic — trimming it corrupts link rendering. (5) mysql2's IFNULL-per-CONCAT-arg vs pg's ignore-NULL semantics are intentional asymmetries.
**Probe:** `packages/nocodb/src/db/formulav2/parsed-tree-builder.ts` :35–331 (search_graph resolved `callExpressionBuilder` line-exact 35-331 at pin f7513664f3f3). Runner BLOCKED (no upstream unit tests for the db/ plane) → line-anchored deterministic check.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "callExpressionBuilder mapFunctionName convertDateFormatForConcat", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the rewrite-only switch plus single-exit generic assembler and the dataType-threading through folds; adapt CONCAT/URL handling to host link syntaxes; omit snowflake/databricks branches unless targeted; keep per-function dialect SQL in the host's own mapping module.
