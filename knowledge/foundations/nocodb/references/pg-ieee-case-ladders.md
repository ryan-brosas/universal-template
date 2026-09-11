<!-- capsule-v2 -->
# IEEE-SQL CASE ladder library — how do you compile IEEE-754 division/modulo/sqrt/power/log into Postgres SQL without exploding query size?

**Source:** NocoDB AGPL-3.0 `develop@640fe3b06fb2`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What is the minimal-SQL-text recipe for Airtable-style x/0→±Infinity, 0/0→NaN semantics on a database that RAISES on all of them?

## Connected graph-selected seam
**Path/Symbol:** `packages/nocodb/src/db/formulav2/pg-ieee.ts` (whole file, 117L; helpers :14–:16, :19–:23, :26–:31, :34–:52, :55–:64, :67–:77, :80–:91, :99–:110, :113–:117).
**Signature:** `isPgClient(knex)`, `coalesceNumericOperand(sql,knex)`, `isFiniteSql(expr)`, `ieeeDivisionSql(l,r)`, `ieeeModuloSql(l,r)`, `ieeeSqrtSql(e)`, `ieeePowerSql(b,e)`, `ieeeLogSql(e)`, `ieeeLogBaseSql(b,v)`, `stripNaNSql(expr)`, `excludeNonFiniteSql(expr)` — all pure SQL-text composers.
**Data Shape:** input = already-rendered operand SQL strings; output = raw SQL text; everything typed `'double precision'` (IEEE_TYPE) because pg<14 `numeric` cannot hold Infinity and Number/Decimal columns map to numeric.

### Decisive source
```ts
// Finite test that mentions the operand once. NaN and ±Infinity both fail it —
// pg ranks NaN above every number, so `abs(NaN) < Infinity` is false — and NULL
// stays NULL. Spelling it out with three <> comparisons would inline the
// operand three times, which matters because these nest.
export function isFiniteSql(expr: string): string {
  return `abs(${expr}) < 'Infinity'::${IEEE_TYPE}`;
}
// pg's own arithmetic *is* IEEE once an Infinity exists, so `x * Infinity`
// resolves all three cases with the correct sign (5→Infinity, -5→-Infinity,
// 0→NaN, NULL→NULL). That keeps each operand to two appearances; branching on
// the sign of `left` instead would inline it three times, and since `/` is
// left-associative the outer left operand is the inner CASE — chained division
// would then grow 3ⁿ instead of 2ⁿ.
```

**Flow:** every guard is a CASE that proves domain-membership cheaply then falls into pg's own operator: division tests only the divisor (`x * 'Infinity'` resolves sign+zero cases); modulo guards divisor≠0 AND finite-left because MOD routes through numeric (no float8 overload) and the cast raises at pg<14; sqrt/log use `< 0` / `<= 0` so NULL and NaN land in the ELSE where the fn maps them to themselves; two-arg LOG negates the in-domain test so NULL falls to ELSE ('NaN' via NULLIF later reads as blank); power guards negative-base×non-integer-exponent ONLY — pow(-Infinity, 2)=Infinity must survive; comparisons strip NaN via `NULLIF(expr,'NaN')` because pg ranks NaN above every number so bare `x > 100` takes the true branch.
**Invariant:** (1) Operand-mention count is the complexity metric — nested composition makes 3-mention branches exponential; every helper here keeps ≤2 mentions. (2) `abs(x) < 'Infinity'` is THE finite test (NaN fails it too, NULL stays NULL). (3) All literals cast to double precision, never numeric. (4) LOG(b,+Inf) returns NaN while one-arg log(+Inf)=Infinity — accepted imprecision because representing it needs a numeric cast pg<14 rejects and ln(x)/ln(b) loses precision for every real input.
**Probe:** `grep -c "CASE WHEN" packages/nocodb/src/db/formulav2/pg-ieee.ts` → 8; `sed -n '26,31p' …pg-ieee.ts` shows isFiniteSql verbatim. No upstream unit suite (caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "pg-ieee ieeeDivisionSql isFiniteSql excludeNonFinite", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the whole library as a unit (helpers + mention-count discipline + float8 typing); adapt literal spellings per dialect; omit nothing — each helper has a distinct consumer. Caveat: no direct upstream test.
