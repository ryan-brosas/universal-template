<!-- capsule-v2 -->
# blank-NaN binary semantics — when must a formula compiler COALESCE blanks to 0 and strip NaN from comparisons?

**Source:** NocoDB AGPL-3.0 `develop@640fe3b06fb2`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Once division can produce NaN/±Infinity, what must a binary-expression builder change BEFORE composing operands, and which data types trigger it?

## Connected graph-selected seam
**Path/Symbol:** `packages/nocodb/src/db/formulav2/parsed-tree-builder.ts:binaryExpressionBuilder` (:478–:733; capture :478–:480, coalesce gate :500–:518, NaN strip :557–:568, `/`+`%` dispatch :718–:732).
**Signature:** `binaryExpressionBuilder({ pt, knex, ... }): Promise<{ builder }>` — mutates `pt` operand nodes then renders both sides.
**Data Shape:** `pt.left.dataType`/`pt.right.dataType` captured BEFORE the `/` rewrite (:478); operators gated: `+ - * / % < > <= >= = !=`.

### Decisive source
```ts
// The `/` rewrite below replaces the operand nodes with FLOAT() wrappers that
// carry no dataType, so capture the operand types first.
const leftDataType = pt.left.dataType;
...
// Blank numerics behave as 0 in arithmetic and comparisons (pg only).
// Applied in every mode, not just display: if display coalesced but sort did
// not, a blank operand would render as a number yet sort as NULL.
if (isPgClient(knex) && [...ops].includes(pt.operator)) {
  const isDivision = pt.operator === '/';
  if (isDivision || leftDataType === FormulaDataTypes.NUMERIC) {
    left = coalesceNumericOperand(left, knex);
  }
```

**Flow:** capture operand types → FLOAT-wrap `/` operands (dataType lost by design) → render sides → pg-only COALESCE(x,0) on numeric-typed operands (all modes) → ordering-comparison numeric coercion (pre-existing) → pg-only `NULLIF(x,'NaN')` wrap on NUMERIC-typed operands inside ordering comparisons → compose `${left} ${op} ${right}` → final dispatch: pg `/` always `ieeeDivisionSql` (a divide-by-zero is a VALUE, not a mode), pg `%` always `ieeeModuloSql` (the COALESCE above turns a blank divisor into literal 0 which pg rejects), non-pg `/` keeps the legacy NULLIF-divide-by-zero branch.
**Invariant:** (1) Operand types must be captured BEFORE the FLOAT() rewrite — the rewritten nodes carry no dataType and the later NaN-strip would silently stop firing. (2) Coalesce applies in EVERY mode (display+sort+filter): partial adoption makes a blank render as 0 but sort as NULL. (3) The NaN strip uses the SAME helper (`stripNaNSql`) as the filter layer so the two layers cannot drift; it fires only for ordering comparisons because eq/neq compare the displayed token and must still match 'NaN'. (4) The IEEE `/` form is unconditional on pg — aggregation drops non-finite rows at ITS own site (`excludeNonFiniteSql`), nothing threads a mode through recursion.
**Probe:** `grep -c "isPgClient(knex)" packages/nocodb/src/db/formulav2/parsed-tree-builder.ts` → 4; `sed -n '478,480p' …parsed-tree-builder.ts` shows the capture comment. No upstream unit suite for formulav2 (runner-blocked caveat, unchanged from prior passes).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "binaryExpressionBuilder parsed tree builder division", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt capture-before-rewrite, mode-uniform blank→0, ordering-only NaN strip, unconditional IEEE `/`+`%` dispatch on pg; adapt operator sets and type enums; omit legacy non-pg divide handling only if your host never divides. Caveat: no direct upstream test.
