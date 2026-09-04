<!-- capsule-v2 -->
# formula output guardrails — how do you stop a formula from crashing the Node process or the DB without changing what valid formulas compute?

**Source:** nocodb (Sustainable Use License) `develop@f7513664f3f3b7286023a7e832a8333808f7557b`; Codebase Memory `nocodb`. **Question:** Where are the query-length and cell-value length limits enforced on formula output, and why is the length wrapper applied only at the outermost expression?

## formula output guardrails
**Path/Symbol:** `packages/nocodb/src/db/formulav2/formula-query-builder.helpers.ts:wrapFormulaWithMaxLength` (:83–128) + `getFormulaOutputMaxLength` (:70–76) + `formulaOutputsRawJson` (:25–54); enforced in `formulaQueryBuilderv2.ts` :566–608.
**Signature:** `wrapFormulaWithMaxLength({knex, builder, maxLength}): Knex.Raw`; `getFormulaOutputMaxLength(): number` (env `NC_FORMULA_MAX_OUTPUT_LENGTH`, default `NC_MAX_TEXT_LENGTH` = 100k); `formulaOutputsRawJson(node): boolean`.
**Data Shape:** input `builder` is a knex Raw/QueryBuilder (may itself carry `?` bindings from nested string literals/subqueries); output is one raw wrapping it; `len` is INLINED as an integer literal, never bound.

### Decisive source
```ts
// helpers :92–102 — single binding + inline literal length (positional-binding safety)
const len = Math.max(1, Math.floor(maxLength));
switch (knex.clientType()) {
  case 'pg':      return knex.raw(`SUBSTR((?)::text, 1, ${len})`, [builder]);
  case 'mssql':   return knex.raw(`SUBSTRING(CAST(? AS NVARCHAR(MAX)), 1, ${len})`, [builder]);
  case 'oracledb':return knex.raw(`SUBSTR(TO_CLOB(?), 1, ${len})`, [builder]); // VARCHAR2 caps at 4000/32767
  ...
}
// caller :571–585 — compile-time SQL-size ceiling (500k chars)
if (sqlLength > 500 * 1000) { TelemetryHandlerService.sendPriorityError(...{error_type:'FORMULA_TOO_LONG_ERROR'}...);
  NcError.get(context).formulaError(`The generated query for ... exceeds the maximum allowed length...`); }
// caller :598–608 — outermost-only, STRING-only, JSON-exempt
if (qb?.parsedTree?.dataType === FormulaDataTypes.STRING && qb.builder &&
    !formulaOutputsRawJson(qb.parsedTree)) {
  qb.builder = wrapFormulaWithMaxLength({ knex, builder: qb.builder, maxLength: getFormulaOutputMaxLength() });
}
```

**Flow:** after `_formulaQueryBuilder` returns, two guardrails fire in order: (1) COMPILE-TIME — render the SQL via `qb?.builder?.toSQL?.().sql?.length` inside its own try/catch (rendering may itself throw) and hard-fail anything over 500,000 chars with a user-facing "simplify the formula" error plus a priority telemetry event; this stops pathological nesting from crashing the server during generation. (2) RUNTIME — if the parsed tree's dataType is STRING and the formula does not produce raw JSON, wrap the WHOLE expression so the DATABASE truncates each rendered value to ≤100k chars: REPEAT/CONCAT-over-lookups can produce strings big enough that V8 (`ERR_STRING_TOO_LONG`, ~512MB cap) or the pg protocol read kills the Node process — a failure site nobody can catch. `formulaOutputsRawJson` walks IF/SWITCH result branches (null branches skipped; SWITCH results at even indices ≥2 plus trailing else when arity even) and treats `JSON_EXTRACT` as always-raw: casting jsonb to ::text would change the VALUE representation (adds quotes), so those formulas are exempt — they also cannot grow unbounded since they only read already-stored JSON.
**Invariant:** (1) The length argument MUST be inlined as a floored positive integer, never a second `?` binding — knex flattens nested builders' bindings positionally, so a trailing placeholder would STEAL a slot from the inner subquery and corrupt the statement. (2) Oracle must use `TO_CLOB` not `CAST(x AS CHAR)` (that reads as CHAR(1), truncating every cell to one character; CAST of CLOB raises ORA-25137). CLOB results can't GROUP BY/DISTINCT (ORA-22849) — acceptable because no caller groups by raw formula output. (3) The wrapper applies ONLY at the outermost call — nested formula references go through `_formulaQueryBuilder` directly and skip it, otherwise every nesting level would re-truncate (and re-cast) already-bounded values. (4) Only STRING-datatype trees are wrapped; numeric/date typing stays untouched.
**Probe:** `packages/nocodb/src/db/formulav2/formula-query-builder.helpers.ts` :83–128 (per-dialect table), `formulaQueryBuilderv2.ts` :566–608 (both gates). Runner BLOCKED (no upstream unit tests for db/ plane) → line-anchored deterministic check.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "wrapFormulaWithMaxLength getFormulaOutputMaxLength formulaOutputsRawJson", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt compile-time SQL-length refusal + runtime DB-level SUBSTR capping with the outermost/string-only/raw-JSON-exempt rule and the single-binding-plus-inline-literal binding shape; adapt the per-dialect cast table to host dialects; omit telemetry event plumbing.
