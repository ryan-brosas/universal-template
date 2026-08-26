<!-- capsule-v2 -->
# formula reference scan — how do you find every formula/button column that references a given column before deleting it?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** getFormulasReferredTheColumn walks parsed formula ASTs — what node types matter and which button columns are exempt?

## formula reference scan
**Path/Symbol:** `packages/nocodb/src/helpers/formulaHelpers.ts` — whole file 46L: `getFormulasReferredTheColumn` (:7–46).
**Signature:** `getFormulasReferredTheColumn(context, {column, columns}, ncMeta?) → Promise<Column[]>`.
**Data Shape:** matches Identifier nodes whose `name` equals EITHER `column.id` OR `column.title` (formulas store raw text; ids appear when formulas were built programmatically).

### Decisive source
```ts
// :18–27 — the recursive matcher:
const fn = (pt) => {
  if (pt.type === 'CallExpression') {
    return pt.arguments.some((arg) => fn(arg));
  } else if (pt.type === 'Literal') {
  } else if (pt.type === 'Identifier') {
    return [column.id, column.title].includes(pt.name);
  } else if (pt.type === 'BinaryExpression') {
    return fn(pt.left) || fn(pt.right);
  }
};
// :29–44 — async reduce + button gate:
if (c.uidt !== UITypes.Formula && c.uidt !== UITypes.Button) return columns;
const formula = await c.getColOptions<FormulaColumn | ButtonColumn>(context, ncMeta);
if (UITypes.Button === c.uidt && (formula as ButtonColumn)?.type !== 'url')
  return columns;
if (formula.formula && fn(formulaJsep(formula.formula))) {
  columns.push(c);
}
```

**Flow:** iterate candidate columns sequentially via PROMISE-REDUCE (each getColOptions awaited in chain) → skip non-Formula/non-Button → for Buttons only `type === 'url'` carries a real formula → parse with SDK `formulaJsep` → walk: CallExpression checks ARGUMENTS ONLY (not the callee name), BinaryExpression both sides, Identifier id-or-title match, Literal never.
**Invariant:** Callee names are deliberately ignored — a column named "ROUND" is not referenced by `ROUND(...)` usage. The dual id/title match is required because persisted formulas may embed either form. Sequential reduce (not Promise.all) keeps meta query order deterministic.
**Probe:** `grep -c "formulaJsep(formula.formula)" packages/nocodb/src/helpers/formulaHelpers.ts` → `1`; `grep -c "'url'" packages/nocodb/src/helpers/formulaHelpers.ts` → `1`.
**Coverage caveat:** grep-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "getFormulasReferredTheColumn formulaJsep", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-node walker and url-only button exemption; adapt jsep parser to host; omit nothing — skipping the button gate breaks button-column deletion guards.
