<!-- capsule-v2 -->
# Formula filter/sort routing — how does a formula column borrow another type's verifier, and when does its value become a bound number?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How are filters on Formula columns validated and compiled without duplicating every target type's logic?

## FormulaGeneralHandler
**Path/Symbol:** `packages/nocodb/src/db/field-handler/handlers/formula/formula.general.handler.ts` — applySort :16-46; filter :48-93; verifyFilter :95-149.
**Signature:** `verifyFilter(filter, column, options) → re-dispatches via options.fieldHandler.verifyFilter` on a CLONED Column with uidt swapped to the formula's data-type mapping (BOOLEAN→Checkbox, DATE→DateTime, INTERVAL→Time, NUMERIC→Decimal, STRING/default→SingleLineText; display_type meta wins first).
**Data Shape:** filter value coercion: DATE formulas pass the raw string; everything else binds `knex.raw('?', [+filter.value | filter.value ?? null])` — numeric conversion ONLY when dataType===NUMERIC && !isNaN(+value).

### Decisive source
```ts
// :73-80 — the builder rides in as customWhereClause for conditionV2:
return parseConditionV2(baseModelSqlv2,
  new Filter({ ...filter, value }) as any,
  aliasCount, alias,
  builder);                       // ← compiled formula SQL becomes the LHS
// :26-31 — literal-only formulas can't be ORDERed meaningfully:
// Pure literal — `ORDER BY '<literal>' is meaningless and some
// dialects reject it; ORDER BY 1 is a portable no-op.
if (parsedTree?.type === 'Literal') { qb.orderBy(knex.raw('?', [1]) as any, direction, nulls); return; }
```

**Flow:** applySort compiles the formula via formulaQueryBuilderv2 and orders by the builder (Literal short-circuits to ORDER BY 1) → filter compiles identically then hands {builder-as-customWhereClause, coerced value} to parseConditionV2 so ALL generic ops work against the computed expression → verifyFilter maps dataType → uidt and re-enters THE DISPATCHER with the cloned column, inheriting that type's supported-op table and value validation.
**Invariant:** (1) The clone-and-re-dispatch pattern means new per-type op rules apply to formulas automatically — but ONLY those keyed on uidt; dialect handlers keyed by the ORIGINAL registry entry still see Formula. (2) Numeric binding must go through `?` — interpolating +value into SQL breaks negative/decimal literals on locale-sensitive engines. (3) ORDER BY 1 (positional) not a raw literal: some engines reject constant ORDER BY expressions.
**Probe:** No unit tests upstream at pin. Deterministic probe: grep "portable no-op" (:28); search_graph resolves `FormulaGeneralHandler.verifyFilter Method ... :90-131` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "FormulaGeneralHandler", limit: 5 });
```

## Verdict
Adopt compile-once-then-delegate shape + typed value coercion; adapt dataType map; omit Rollup twin's Links/BT-like special case only if you lack v2 junction columns. Caveat: no direct tests at pin.
