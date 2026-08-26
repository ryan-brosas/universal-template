<!-- capsule-v2 -->
# Selector parsing + specificity cache — how do you parse AST selectors once, extract candidate node types, and order listener calls deterministically?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you turn rule selector strings into cheap per-node-type dispatch tables with a stable call order?

## esquery wrapper + ESQueryParsedSelector
**Path/Symbol:** `lib/linter/esquery.js:parse` (:288–310), `ESQueryParsedSelector.compare` (:101–107), `analyzeParsedSelector` (:148–231), `trySimpleParseSelector/tryParseSelector` (:239–281), module-level `selectorCache` (:114).
**Signature:** `parse(source) → ESQueryParsedSelector{source, isExit, root, nodeTypes, attributeCount, identifierCount}`; `compare(other)` sorts by attribute count → identifier count → alphabetical source.
**Data Shape:** `nodeTypes` is `string[]|null`: null means "could match ANY type" (wildcards, attribute-only, class selectors other than `:function`); compound selectors INTERSECT component types; `matches` unions them; `:exit` suffix is stripped before parse and stored as the `isExit` flag.

### Decisive source
```js
const cleanSource = source.replace(/:exit$/u, "");
const parsedSelector = trySimpleParseSelector(cleanSource) ?? tryParseSelector(cleanSource);
// fast path: "*" and /^[a-z]+$/iu never touch the real parser
if (selectorCache.has(source)) return selectorCache.get(source);
// ...
case "compound": {
  const types = selector.selectors.map(analyzeSelector).filter(Boolean);
  if (!types.length) return null;                 // any component unknown ⇒ unknown
  return intersection(...types);                  // all known ⇒ only their intersection can match
}
case "class":
  if (selector.name === "function") return ["FunctionDeclaration","FunctionExpression","ArrowFunctionExpression"];
  return null;
```

**Flow:** every distinct selector string is parsed exactly once process-wide (unbounded Map — selectors come from rule code, a bounded vocabulary). Downstream (`source-code-traverser.js:ESQueryHelper`) buckets parsed selectors by nodeType (or anyType), pre-sorts each bucket by specificity, and per node merge-walks the two sorted lists so matching selectors emerge already in call order. Parse failures are rethrown as SyntaxError with offset position and cause.
**Invariant:** specificity is (attributes, identifiers, lexicographic) — NOT registration order; the cache key is the RAW source (with `:exit`), while parsing uses the cleaned source; type-bucketing is an optimization that must remain conservative (`null` = any type) or selectors silently stop firing.
**Probe:** `tests/lib/linter/esquery.js` (:26–139 compare ordering; :140–261 parse incl. nodeTypes extraction; :282+ matches/compare suites).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "ESQueryParsedSelector analyzeParsedSelector trySimpleParseSelector", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.esquery.parse" });
```

## Verdict
Adopt process-wide memoized parsing + static nodeType extraction + three-key specificity; adapt the pseudo-class table to your AST; bound the cache if selectors are user-input-driven.
