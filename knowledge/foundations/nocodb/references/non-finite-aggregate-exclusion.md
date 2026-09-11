<!-- capsule-v2 -->
# non-finite aggregate poisoning — where must each aggregation consumer drop IEEE rows, and why does the count family keep them?

**Source:** NocoDB AGPL-3.0 `develop@640fe3b06fb2`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** A single NaN row poisons SUM/AVG/MAX for a whole column — at which sites must rows be dropped to NULL, and why not everywhere?

## Connected graph-selected seam
**Path/Symbol:** `packages/nocodb/src/db/genRollupSelectv2.ts` (:35–:42 allowlist, :222–:251 exclusion site) · `packages/nocodb/src/dbQueryClient/cross-db-utils/applyAggregation.ts` (:105–:122) · `services/formula-column-type-changer/pg-data-migration.ts` (:54–:74, :83–:92).
**Signature:** rollup: gate `NON_FINITE_EXCLUDING_ROLLUPS.includes(rollup_function)` over `excludeNonFiniteSql(resolvedFormulaSql)`; aggregation: `dbDriver.raw(excludeNonFiniteSql('??'), [column_name_query, column_name_query])`.
**Data Shape:** allowlist exactly `{sum, sumDistinct, avg, avgDistinct, min, max}`; gate requires pg ∧ Formula ∧ parsed-tree dataType NUMERIC ∧ builder (not string) select.

### Decisive source
```ts
// Numeric rollups a non-finite value would poison. `count`/`countDistinct` are
// deliberately absent — they must keep seeing every row.
const NON_FINITE_EXCLUDING_ROLLUPS = [
  'sum', 'sumDistinct', 'avg', 'avgDistinct', 'min', 'max',
];
...
// since the value lands on a Rollup column rather than a Formula one,
// convertFormulaNonFinite skips it and JSON.stringify blanks it to null —
// a wrong value that reads as no value. The count family is deliberately
// excluded: an Infinity cell is not an empty cell.
```

**Flow:** three consumers, three binding styles: genRollupSelectv2 composes EXCLUDED SQL TEXT into knex.raw (re-binding this Raw would strip the inner `\?` escape — same dance as the pre-existing subquery note above it); applyAggregation wraps the builder as a DOUBLE-bound `??` placeholder (excludeNonFiniteSql mentions the expression twice → two binds); pg-data-migration re-applies `\?` escaping after toQuery() before wrapping, and gates on destination column numeric-ness (Number=bigint/Rating=int raise `out of range`; float8 Percent holds ±Inf but READS BACK AS NULL; text keeps the token unwrapped).
**Invariant:** (1) Count family NEVER excluded — an Infinity cell is not an empty cell. (2) Exclusion fires only on pg ∧ NUMERIC-formula ∧ numeric-aggregate; cells/filters/sorts/group keys want the value itself, never the exclusion. (3) Rollup output bypasses convertFormulaNonFinite (it's a Rollup column, not Formula), hence exclusion MUST happen at its own site or JSON.stringify silently renders a poisoned value as null — a wrong value that reads as no value. (4) Each consumer uses the binding style its call position allows; mixing text-composition and placeholder-binding breaks either the escape or the binds.
**Probe:** `sed -n '35,42p' packages/nocodb/src/db/genRollupSelectv2.ts` allowlist verbatim; `sed -n '105,122p' …applyAggregation.ts` two-bind wrap verified. No upstream unit suite (caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "applyAggregation excludeNonFinite rollup formula aggregation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the per-consumer exclusion map + count-family exemption + three binding recipes; adapt aggregate names; omit migration-site handling if your host has no formula-type-changer. Caveat: no direct upstream test.
