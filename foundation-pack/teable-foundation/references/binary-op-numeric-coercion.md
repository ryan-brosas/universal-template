<!-- capsule-v2 -->
# binary-op-numeric-coercion — Which comparison/arithmetic operands get safe numeric casts, and when is the cast deliberately skipped?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does `"5" > 3` compile without a Postgres type error — and why does `x = ""` skip coercion?

## Infer both operand types; cast string side for comparisons and arithmetic; blank-like equality exempt
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/sql-conversion.visitor.ts:visitBinaryOp` (:829-958, comparison block :841-884).
**Signature:** `visitBinaryOp(ctx: BinaryOpContext): string`; helpers `inferExpressionType`, `isBlankLikeExpression`, `safeCastToNumeric` (dialect `coerceToNumericForCompare`), `coerceBooleanToNumeric`.
**Data Shape:** comparisons needing coercion: `> < >= <= = != <>`; arithmetic: `* / - %`; `+` has its own string/datetime→concat vs numeric branch; `&` ALWAYS concatenates.

### Decisive source
```ts
if (operator.text && needsNumericCoercion(operator.text)) {
  const isEqualityComparison = ['=', '!=', '<>'].includes(operator.text);
  ...
} else if (leftType === 'number' && rightType === 'string' &&
    !(isEqualityComparison && rightIsBlankLike)) {
  right = this.safeCastToNumeric(right);
} else if (leftType === 'string' && rightType === 'number' &&
    !(isEqualityComparison && leftIsBlankLike)) {
  left = this.safeCastToNumeric(left);
}
...
// arithmetic (except '+') coerces strings so "text * 3" works:
const needsArithmeticNumericCoercion = (op) => ['*', '/', '-', '%'].includes(op);
```

**Flow:** visit children → typed metadata attached to formulaQuery → infer literal/field types per side → boolean-vs-number promotes BOTH sides (boolean through truthiness score, number through safe cast) → number-vs-string casts the string UNLESS it's an equality against a blank-like expression (empty string/NULL must stay comparable as text — casting '' to numeric yields NULL and would break "is empty" semantics) → dispatch operator.
**Invariant:** the blank-equality exemption IS the subtle contract: coercing one side of `= ''` changes NULL/'' semantics, so equality keeps text form while ordering casts. `&` never becomes addition even for two numbers.
**Probe:** upstream spec pins sibling behavior (`select-query.postgres.spec.ts` truthinessScore + IF cases); static byte-exact: `grep -n 'needsNumericCoercion(operator.text)' sql-conversion.visitor.ts` → :847.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"safeCastToNumeric","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the coercion matrix incl. exemptions. Adapt type inference to your field model. Omit nothing.
