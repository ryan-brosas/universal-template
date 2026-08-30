<!-- capsule-v2 -->
# Filter-tree shape parser — how do you convert arbitrary user filter JSON into an indexable operator-family summary without executing or storing it?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How is a nested conjunction/filterSet tree reduced to condition counts, depths, and per-leaf operator families that survive JSON-or-object inputs?

## Depth-tracking walk with field-reference detection
**Path/Symbol:** `packages/v2/table-query-ops/src/queryConfigShape.ts`: `parseFilterStats` (:182-228), `walk` (:187-217), `containsFieldReference` (:296-305), `toOperatorFamily` (:373-418), `buildShape` formula-aware leaf mapping (:83-129), `toFormulaAwareOperatorFamily` (:351-371).
**Signature:** `parseFilterStats(value: unknown): ParsedFilterStats | undefined`; `toOperatorFamily(operator: string, isFieldReference?: boolean): TableQueryOperatorFamily`.
**Data Shape:** leaf = `{fieldId, operator, isFieldReference}`; stats = `{conditionCount, andDepth, orDepth, leaves}`; depth = MAX over children (not sum), incremented per conjunction level (`conjunction==='or'` bumps orDepth only). Unknown operators → `'unknown'` family, never dropped.

### Decisive source
```ts
if (typeof item.fieldId === 'string' && typeof item.operator === 'string') {
  leaves.push({ fieldId: item.fieldId, operator: item.operator,
                isFieldReference: item.isSymbol === true || containsFieldReference(item.value) });
  return depth;
}
if (!Array.isArray(item.filterSet)) return depth;
const nextDepth = { andDepth: conjunction === 'or' ? depth.andDepth : depth.andDepth + 1,
                    orDepth:  conjunction === 'or' ? depth.orDepth + 1  : depth.orDepth };
return item.filterSet.reduce((maxDepth, child) => { …Math.max… }, nextDepth);
```

**Flow:** parse (string→JSON via tolerant helpers) → walk collecting leaves + max depths → buildShape filters leaves to KNOWN table fields, resolves formula fields through `analyzeFormulaIndexability` (parse failure ⇒ `formula_parse_failed` skipped-reason shape, sqlTranslatable=false), REWRITES single-source formula_source leaves onto their referenced source field id, then maps the operator family through the formula-aware ladder: unstable ⇒ `formula_result`; pushdown-supported stable source ⇒ its pushdown family (text_contains/text_prefix/equality/range); expression ⇒ `formula_result`.
**Invariant:** Values are inspected ONLY for structural predicates (`fieldId`/`field` key presence) — never captured. Field-reference operands reclassify the whole leaf as a link-family predicate so index advice never suggests a btree for "column equals other-column". The formula_source rewrite is what makes "search on IF(a,b,c)" advise an index on `a`, not on the formula output.
**Probe:** `savedViewConfigObservation.spec.ts:113` "extracts formula source-field evidence without storing formula literals"; :146 "extracts IF predicate pushdown evidence"; `relationFieldConfigObservation.spec.ts:73`.
**Coverage caveat:** queryConfigShape has no dedicated spec file — pinned indirectly through both observation-extractor specs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "parseFilterStats toFormulaAwareOperatorFamily analyzeFormulaIndexability", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt max-depth tree reduction + structural-only value inspection + the formula-source rewrite; adapt the operator→family table to your filter DSL; omit teable's specific operator strings.
