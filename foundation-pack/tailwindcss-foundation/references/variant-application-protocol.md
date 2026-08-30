<!-- capsule-v2 -->
# Variant application protocol — when does a variant make a rule inapplicable, and how do compound variants compose without cross-contamination?

**Source:** tailwindcss MIT `main@90f8ff41c8e2a4d17bc76921e23e9d672123da76`; Codebase Memory `tailwindcss`. **Question:** How should `[>img]:flex`, `group-hover:[&_p]:flex`, and `not-foo:…` (at-rule variant) each behave, and how does "cannot apply" propagate?

## applyVariant recursion
**Path/Symbol:** `packages/tailwindcss/src/compile.ts:177-269` (`applyVariant`), called from `compileAstNodes` (`compile.ts:159-166`).
**Signature:** `applyVariant(node: Rule, variant: Variant, variants: Variants, depth = 0): null | void`.
**Data Shape:** `Variant` = arbitrary `{ selector, relative }` | compound `{ root, variant }` | simple root lookup in `variants`; return contract `null` = not applicable, `void` = applied.

### Decisive source
```ts
if (variant.kind === 'arbitrary') {
  // Relative selectors are not valid as an entire arbitrary variant, only as
  // an arbitrary variant that is part of another compound variant.
  if (variant.relative && depth === 0) return null
  ...
}
...
if (variant.kind === 'compound') {
  // ... we provide an isolated placeholder node to the variant.
  let isolatedNode = atRule('@slot')
  let result = applyVariant(isolatedNode, variant.variant, variants, depth + 1)
  if (result === null) return null

  if (variant.root === 'not' && isolatedNode.nodes.length > 1) {
    // The `not` variant cannot negate sibling rules / at-rules ...
    return null
  }

  for (let child of isolatedNode.nodes) {
    // ... This also means the entire variant as a whole is not
    // applicable to the rule and should generate nothing.
    if (child.kind !== 'rule' && child.kind !== 'at-rule') return null
    let result = applyFn(child, variant)
    if (result === null) return null
  }
```

**Flow:** for each variant left-to-right in `candidate.variants`: apply to the rule; `null` aborts the *whole candidate* (`compileAstNodes` returns `[]`, so the raw string is reported invalid). Arbitrary variants wrap nodes in one child rule; variant-generated `@scope` at-rules are double-wrapped in context markers (`source: 'variant'` outer, slotted content marked `source: 'user'`) so hoisting uses variant semantics instead of native CSS nesting. Compound variants (`group-*`, `peer-*`, `not-*`, `has-*`) first apply their inner variant to an isolated `@slot` placeholder, then apply the compound root's function to those children, then graft results back by replacing empty rule/at-rule shells with the original nodes.
**Invariant:** `null` is viral upward but never silently swallowed — every call site checks it; a discarded candidate generates zero CSS and is remembered as invalid. The isolated-node trick guarantees `group-hover:[&_p]:flex` prefixes only the `group-hover` part with `.group`, not the `&_p` part. `@slot` never reaches output CSS.
**Probe:** `packages/tailwindcss/src/index.test.ts:5006` "at-rule-only variants cannot be used with compound variants" — `foo:flex` and `not-foo:flex` emit CSS while `group-foo:flex`, `peer-foo:flex`, `has-foo:flex` emit nothing; :983 "discards arbitrary variants using relative selectors"; :4730+ pin `@scope` context semantics.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "tailwindcss", query: "applyVariant compound arbitrary slot not variant apply null", filePattern: "packages/tailwindcss/src/*", limit: 10, fields: ["lines"] });
```
Observed top hit: `compile.applyVariant … compile.ts 177-269`, then `variants.Variants.compound … variants.ts 137-150`.

## Verdict
Adopt the tri-state application contract (applied / not-applicable-null / recursion depth guard), the `@slot` isolation pattern, and the `not`-sibling restriction. Adapt the concrete built-in variant functions and `Variants.compare` ordering. Omit the specific context-marker vocabulary unless your host also mixes user-authored CSS nesting into the same AST.
