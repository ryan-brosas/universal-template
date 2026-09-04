<!-- capsule-v2 -->
# Selector emission-order conformance — how do you prove a traversal fires selectors in exactly the documented order across exotic ASTs?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** What test machinery pins that `A > B`, `:exit`, attribute, and specificity-ordered selectors all fire at the right nodes — including non-standard and TypeScript-shaped trees?

## assertEmissions harness
**Path/Symbol:** `tests/lib/linter/source-code-traverser.js:createMockSourceCode(ast)` (:54–110 pre-generated step arrays), `getEmissions` (:406–424 spy visitor), `assertEmissions(sourceText|ast, possibleQueries, getExpectedEmissions)` (:436–493), "traversing the entire non-standard AST" describe (:732–866).
**Signature:** expected emissions are `[selector, nodeReference]` pairs asserted with deepStrictEqual PLUS per-element strictEqual on the node ("Expected a node instance from the AST").
**Data Shape:** mock SourceCode yields steps eagerly built by recursive walk skipping `{parent, loc, tokens, comments, range}`; custom visitor keys supplied via `vk.unionWith({ClassDeclaration: [decorators…implements…body]})`.

### Decisive source
```js
actualEmissions.forEach((actualEmission, index) => {
  assert.strictEqual(actualEmission[1], expectedEmissions[index][1],
    "Expected a node instance from the AST");   // identity, not structural equality
});
// TS-flavored case: parse class A implements B {} shape as plain object,
// extend visitor keys via vk.unionWith(...), assert :first-child hits implements[0]
```

**Flow:** each call registers ONLY the queried selectors on a fresh visitor → traverse → filter emissions to the query set → compare full order.
**Invariant:** node IDENTITY assertion catches engines that clone/rebuild nodes during dispatch (structural equality would pass; real rules hold references). The 23-case matrix pins: enter-before-child/exit-after ordering; descendant vs child combinator discrimination; attribute-value matching incl. `[name.length=3]`; wildcard and `:not` composition; comma-list selector emission under ONE registration; specificity ordering of co-matched selectors (0→1→2 identifier ladder with attribute tiebreaks); JSX sibling combinator over espree jsx parse; foreign visitor-keys via unionWith for TS `implements`. This is the executable specification the ESQueryHelper merge-walk must satisfy.
**Probe:** `tests/lib/linter/source-code-traverser.js` (:398+ standard matrix; :666–700 specificity ladder case; :848–866 unionWith/:first-child TS case).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "assertEmissions createMockSourceCode getEmissions", limit: 10 });
```

## Verdict
Adopt the emissions-with-identity-assertion pattern to pin ANY event-dispatch order; adopt step-array mocking to test traversers without parsers; adapt selector vocabulary.
