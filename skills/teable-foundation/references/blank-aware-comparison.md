<!-- capsule-v2 -->
# blank-aware-comparison — How do `=`/`<>` compile so that '' and NULL behave as one blank class across types?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What normalization makes `field = BLANK()` correct for numeric, text, and json fields alike?

## Blank literals force both sides into normalized text; numeric-comparable pairs stay native
**Path/Symbol:** `apps/nestjs-backend/src/db-provider/select-query/postgres/select-query.postgres.ts:buildBlankAwareComparison` (:676-733); twin at `generated-column-query.postgres.ts:214-270`.
**Signature:** `private buildBlankAwareComparison(operator: '=' | '<>', left, right, metadataIndexes?: {left?, right?}): string`.
**Data Shape:** decision inputs per side: isEmptyStringLiteral (`''`), isNullLiteral (case-insensitive NULL), isTextLikeExpression, shouldCoalesceNumericComparison.

### Decisive source
```ts
if (!normalizeText && (leftIsNumericComparable || rightIsNumericComparable)) {
  // numeric pair: collapse each side via toNumericSafe then compare natively
}
if (!normalizeText) return `(${left} ${operator} ${right})`;
// blank/text path: every operand becomes COALESCE(NULLIF(text, ''), '')
const normalizeOperand = (value, isEmptyLiteral, isNullLiteral, idx) =>
  isEmptyLiteral || isNullLiteral ? "''" : this.normalizeBlankComparable(value, idx);
```

**Flow:** any blank literal OR text-like side on either side routes BOTH operands through `normalizeBlankComparable` (= coerceToTextComparable + COLLATE + `COALESCE(NULLIF(x,''),'')`) so '' and NULL collapse to the same `''`; otherwise numeric-comparable pairs get `collapseNumeric` on the comparable side only; else raw comparison.
**Invariant:** the blank class unification is the point — in Postgres `NULL = ''` is NULL and `1 = ''` errors; after normalization both become a plain text equality. Upstream spec pins it: `generated-column-query.postgres.spec.ts:equal('__weight', query.blank())` expects `COALESCE(NULLIF … ::text … = ''`.
**Probe:** upstream direct spec `generated-column-query.postgres.spec.ts` ("normalizes BLANK() when comparing number fields"); static byte-exact: `grep -n 'normalizeBlankComparable(value, metadataIndex)' select-query.postgres.ts` → :276-281 region (:275).

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"buildBlankAwareComparison","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the three-way dispatch (numeric / raw / blank-normalized). Adapt the blank vocabulary. Omit nothing.
