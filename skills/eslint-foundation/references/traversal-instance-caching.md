<!-- capsule-v2 -->
# Per-language traversal instance cache — how do you make a stateful traverser reusable across files without leaking per-file state?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** Why is SourceCodeTraverser cached per Language in a WeakMap, and what makes sharing safe when the selector tables look per-run?

## SourceCodeTraverser.getInstance
**Path/Symbol:** `lib/linter/source-code-traverser.js:SourceCodeTraverser.instances` (static `WeakMap`, :242), `getInstance(language)` (:252), `traverseSync` esquery construction (:269+).
**Signature:** `static getInstance(language): SourceCodeTraverser`.
**Data Shape:** the cached instance holds ONLY the language; ALL run-specific state (selector buckets, ancestry) is rebuilt per traverseSync call inside ESQueryHelper.

### Decisive source
```js
traverseSync(sourceCode, visitor, { steps } = {}) {
  const esquery = new ESQueryHelper(visitor, {          // fresh EVERY call
    visitorKeys: sourceCode.visitorKeys ?? this.#language.visitorKeys,
    fallback: vk.getKeys,
    matchClass: this.#language.matchesSelectorClass ?? (() => false),
    nodeTypeKey: this.#language.nodeTypeKey,
  });
  const currentAncestry = [];                            // fresh EVERY call
  for (const step of steps ?? sourceCode.traverse()) { ... }
}
```

**Flow:** language object keys the cache → first use constructs → subsequent files reuse the (stateless) instance → per-run visitor selectors and ancestry live only in locals.
**Invariant:** caching is keyed on the LANGUAGE OBJECT IDENTITY, not its name — two structurally identical language objects get separate traversers (test-pinned), which matters because matchesSelectorClass/nodeTypeKey are closures. A WeakMap lets languages be garbage-collected with their plugins. The porting trap: if you hoist ESQueryHelper construction to the constructor for "performance", selector registration from file N+1's rules would merge into file N's buckets — cross-file listener bleed. Steps come pre-generated from `sourceCode.traverse()` so the traverser never assumes a tree shape; STEP_KIND_CALL steps bypass selector matching entirely.
**Probe:** `tests/lib/linter/source-code-traverser.js` (:376–395 per-language identity assertions incl. notStrictEqual across clones; :868–883 invalid-selector SyntaxError).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "SourceCodeTraverser getInstance instances WeakMap", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.source-code-traverser.SourceCodeTraverser.traverseSync" });
```

## Verdict
Adopt the identity-keyed WeakMap + per-call state rebuild pattern for any shared engine object parameterized by plugin-provided config; document WHY the hot path allocates per run or someone will "optimize" it into a correctness bug.
