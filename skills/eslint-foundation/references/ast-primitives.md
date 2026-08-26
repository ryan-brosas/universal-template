<!-- capsule-v2 -->
# AST rule primitives — how do rules inspect property names, parenthesisation, and fix ranges without re-deriving token math?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** Which shared AST helpers carry invariants a rule author (or porter) would otherwise get wrong?

## getStaticPropertyName
**Path/Symbol:** `lib/rules/utils/ast-utils.js:getStaticPropertyName` (:304–334).
**Signature:** `getStaticPropertyName(node): string|null`.
**Data Shape:** accepts `Property | PropertyDefinition | MethodDefinition | TSPropertySignature | TSMethodSignature` (key) or `MemberExpression` (property); recurses through `ChainExpression`.

### Decisive source
```js
if (prop) {
  if (prop.type === "Identifier" && !node.computed) return prop.name;
  return getStaticStringValue(prop);   // literals; computed must still be static strings
}
return null;
```

**Flow:** pick the key/property sub-node by type → non-computed identifiers give their name directly → everything else must resolve to a static string value.
**Invariant:** computed members can still be static (`obj["a-b"]`) — the check is value-staticness, not syntax. Dynamic keys (`obj[a]`, template literals with expressions) return `null`; callers must null-check, never assume a name.
**Probe:** `tests/lib/rules/utils/ast-utils.js` (`getStaticPropertyName` cases incl. computed-string and ChainExpression).

## isParenthesised
**Path/Symbol:** `lib/rules/utils/ast-utils.js:isParenthesised` (:655–666).
**Signature:** `isParenthesised(sourceCode, node): boolean`.

### Decisive source
```js
const previousToken = sourceCode.getTokenBefore(node),
      nextToken = sourceCode.getTokenAfter(node);
return Boolean(previousToken && nextToken) &&
  previousToken.value === "(" && previousToken.range[1] <= node.range[0] &&
  nextToken.value === ")" && nextToken.range[0] >= node.range[1];
```

**Flow:** token immediately before/after → both must exist, be the paren pair, and bracket the node's range without crossing it.
**Invariant:** adjacency plus ordering — a distant `( )` elsewhere doesn't count; extra nested parens are handled because each call checks only the immediate tokens. Fixes that add/remove parens must consult this first or they corrupt valid code.
**Probe:** `tests/lib/rules/utils/ast-utils.js` (`isParenthesised`).

## FixTracker + lazy LazyLoadingRuleMap
**Path/Symbol:** `lib/rules/utils/fix-tracker.js:FixTracker` (:1–125) and `lib/rules/utils/lazy-loading-rule-map.js:LazyLoadingRuleMap` (:1–118).
**Signature:** `FixTracker#replaceTextRange(range, text)` / `retainRange(range)` / `applyFixes()`; `new LazyLoadingRuleMap(Object.entries({ name: () => require("./rule") }))`.
**Data Shape:** FixTracker tracks a "retained" span that merged fixes must not overlap; LazyLoadingRuleMap extends Map whose values are *factory functions*, invoked on first `get`.

### Decisive source
```js
// fix-tracker: fixes are merged only while they respect retained source ranges;
// attempting to fix inside a retained range throws instead of producing overlapping edits.
// lazy-loading-rule-map:
get(name) { this.assertNewName... } // map values called lazily so requiring one rule never loads the whole ruleset
```

**Flow:** rules that emit several coordinated fixes register ranges with the tracker; the map defers `require()` of each core rule until a config enables it.
**Invariant:** multi-fix rules must route edits through the tracker or two suggestions can overlap into an invalid patch; the rules map is perf-critical startup surface — eager loading it regresses cold-start for every consumer.
**Probe:** `tests/lib/rules/utils/fix-tracker.js` (direct) + `tests/lib/unsupported-api.js:48` (`assert.instanceOf(api.builtinRules, LazyLoadingRuleMap)` — the only direct LazyLoadingRuleMap pin; NO dedicated suite exists at pin `c27bc92e`, see lazy-rule-map-freeze coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "getStaticPropertyName isParenthesised FixTracker", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.rules.utils.ast-utils.getStaticPropertyName" });
```

## Verdict
Adopt value-staticness for member names, immediate-token parenthesisation, tracked multi-fix merging, and lazy rule maps; adapt helper naming/API to host SourceCode utilities; omit TS-property-signature node types if your host has no TS flavor. Coverage caveat: `lib/shared/traverser.js` (:202L) remains the generic fallback key walker — port alongside these helpers when visitor keys may be missing.
