<!-- capsule-v2 -->
# formula unary fold — how does `-5` compile, and why is the LiteralNode cast safe?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What does the compiler's UnaryExpression branch actually emit, and what guarantees folding `-arg * 1|-1` cannot read `.value` of a non-literal?

## fn() UnaryExpression branch — sign-fold vs prefix-splice
**Path/Symbol:** `packages/nocodb/src/db/formulav2/formulaQueryBuilderv2.ts:_formulaQueryBuilder.fn` (:468–490); guard contract in `packages/nocodb-sdk/src/lib/formula/validate-extract-tree.ts:1115–1129`.
**Signature:** `(pt: UnaryExpressionNode, prevBinaryOp?: string) => { builder: Knex.Raw }` inside the recursive `fn(pt, prevBinaryOp?)` dispatcher.
**Data Shape:** input is a jsep UnaryExpression node post-type-validation (`operator`, `argument`, `dataType`); output is ONE bound-parameter raw (fold arm) or a prefix-operator raw assembled from the materialized child (splice arm).

### Decisive source
```ts
// formulaQueryBuilderv2.ts :468–490
} else if (pt.type === 'UnaryExpression') {
  let query;
  if (
    (pt.operator === '-' || pt.operator === '+') &&
    pt.dataType === FormulaDataTypes.NUMERIC
  ) {
    query = knex.raw('?', [
      (pt.operator === '-' ? -1 : 1) *
        ((pt.argument as LiteralNode).value as number),   // cast is VALIDATION-guaranteed
    ]);
  } else {
    query = knex.raw(
      `${pt.operator}${(await fn(pt.argument, pt.operator)).builder.toQuery()}`,
    );
  }
  if (prevBinaryOp && pt.operator !== prevBinaryOp) {
    query.wrap('(', ')');
  }
  return { builder: query };
}
```
```ts
// nocodb-sdk validate-extract-tree.ts :1115–1129 — the ONLY admitted unary shape
} else if (parsedTree.type === JSEPNode.UNARY_EXP) {
  // only support -ve values
  if (
    ['-'].includes(parsedTree.operator) &&
    parsedTree.argument.type === JSEPNode.LITERAL &&
    typeof parsedTree.argument.value === 'number'
  ) {
    res.dataType = FormulaDataTypes.NUMERIC;
  } else {
    throw new FormulaError(FormulaErrorType.NOT_SUPPORTED, {},
      `Unary expression '${parsedTree.operator}' is not supported`);
  }
```

**Flow:** the SDK validator runs first (either fresh in `_formulaQueryBuilder` :85–100 or as the persisted `parsed_tree`) and throws `NOT_SUPPORTED` for every unary except `-` over a numeric literal — so at compile time the NUMERIC fold arm always fires for validated trees, emitting a single bound constant (`-5` becomes one `?` binding carrying `-5`). The prefix-splice arm (`op + child.toQuery()`) is defense-in-depth for programmatically supplied / legacy persisted trees that bypass fresh validation: it threads `pt.operator` DOWN as the child's `prevBinaryOp`, so a nested binary with a different operator gets paren-wrapped by the same precedence rule the binary builder uses. After either arm, the node itself wraps in parens only when its own operator differs from the enclosing binary op.
**Invariant:** (1) The `(pt.argument as LiteralNode).value` cast is safe ONLY under the SDK gate — a porter who admits general unaries (e.g. `-columnName`, `!flag`) without adding real arms crashes here reading `.value` of a non-literal, or silently binds `NaN`; extend BOTH the validator and this branch together. (2) The fold must emit ONE bound parameter, not composed SQL like `0 - ?` or `-?` — dialects disagree on literal-prefix negation edge cases and the fold sidesteps all of them. (3) Dropping the `prevBinaryOp = pt.operator` thread in the splice arm flattens precedence for mixed expressions (`-(a)+b` class) — the wrap check compares the CHILD's op against the threaded parent op. (4) `'+'` is accepted by the fold arm but rejected by the current validator (`['-']` whitelist) — keep both sides in sync if the whitelist ever widens.
**Probe:** `grep -n "pt.operator === '-'" packages/nocodb/src/db/formulav2/formulaQueryBuilderv2.ts` → exactly :471 and :475; `grep -n "only support -ve values" packages/nocodb-sdk/src/lib/formula/validate-extract-tree.ts` → exactly :1116. Runner BLOCKED (no upstream unit tests cover db/formulav2; sdk spec validates the throw path only) → line-anchored deterministic checks.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "UnaryExpression operator prevBinaryOp _formulaQueryBuilder", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-arm shape (validation-guaranteed constant fold + precedence-threaded prefix splice) and the single-binding fold output; adapt the operator whitelist only in lockstep between host validator and compiler; omit the SDK error-class plumbing.
