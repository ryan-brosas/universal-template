<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/db/genRollupSelectv2.ts` :220–245 + `dbQueryClient/cross-db-utils/applyAggregation.ts` :105–122.

# Question
Why does the SAME non-finite exclusion need THREE different binding styles at its three consumer sites?

## Path / Symbol
`excludeNonFiniteSql` consumers: applyAggregation (double-bind), genRollupSelectv2 (SQL-text composition), type-changer (escape re-application).

## Signature
```ts
// applyAggregation:      knex.raw(excludeNonFiniteSql('??'), [column_name_query, column_name_query])  // TWO binds
// genRollupSelectv2:     excludeNonFiniteSql(resolvedFormulaSql)  // composed as TEXT, never re-bound
```

## Data Shape
The exclusion wraps a numeric expression so NULL/NaN/±Inf rows drop out of SUM/AVG/MIN/MAX; the count family deliberately keeps every row ("an Infinity cell is not an empty cell").

## Decisive source
genRollupSelectv2.ts:229–233 — the comment names rollup "the second numeric-aggregate consumer of a pg formula, and the only one that doesn't route through applyAggregation — so it needs the same exclusion at its own site. Otherwise a single non-finite row takes the whole aggregate (NaN poisons sum/avg/max; -Infinity wins min), and since the value lands on a Rollup column rather than a Formula one, convertFormulaNonFinite skips it and JSON.stringify blanks it to null — **a wrong value that reads as no value**."
:222–227 — why text-not-raw: the formula SQL was materialized with `\?` escapes (:220–221 referencing parsed-tree-builder.ts:307); "Composed as SQL text, not a nested knex.raw bind — re-binding this Raw would strip the escape."
applyAggregation.ts:117 — the mirror-image constraint: "excludeNonFiniteSql mentions the expression twice, so it needs two binds" when wrapping a live QueryBuilder.
This pass's dbQueryClient reading confirms applyAggregation is the shared prelude for ALL client-side aggregates while rollup stays a parallel site — three binding styles exist because each site receives the expression in a different form (builder vs escaped text vs toQuery output).

## Flow / Invariant
Porter rule: the exclusion FUNCTION is one, but its APPLICATION depends on how the expression reaches you: live builder → wrap+double-bind; pre-materialized escaped text → compose inline, NEVER re-bind; post-toQuery strings → re-apply escapes after composing. Choosing the wrong style either strips escapes (broken SQL) or double-escapes (literal `\?` in query).

## Probe (direct test)
From repo root:
```
grep -n 'only one that does' packages/nocodb/src/db/genRollupSelectv2.ts                       # => 1 (:229)
grep -n 'would strip the escape' packages/nocodb/src/db/genRollupSelectv2.ts                   # => 1 (:228)
sed -n '105,122p' packages/nocodb/src/dbQueryClient/cross-db-utils/applyAggregation.ts | grep -c 'column_name_query,'  # => 2 (the double bind)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"rollup non-finite exclusion escape","limit":3,"detail":"compact"}'
```
→ resolves genRollupSelectv2 region + non-finite family.

## Verdict
**Adopt.** Cross-references existing capsules non-finite-aggregate-exclusion + formula-rollup-escape-composition from the dbQueryClient side: applyAggregation is now confirmed as the third site's routing hub.
