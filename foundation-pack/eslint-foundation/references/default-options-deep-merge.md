<!-- capsule-v2 -->
# Rule options deep-merge — how do `defaultOptions` combine with user options positionally without corrupting object form?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** What is the exact merge semantics when a rule declares meta.defaultOptions and the user supplies a shorter array (or none)?

## deepMergeObjects / deepMergeArrays
**Path/Symbol:** `lib/shared/deep-merge-arrays.js:deepMergeObjects(first, second)` (:23–41) + `deepMergeArrays(first, second)` (:49–61); consumed via `getRuleOptions(configuredRules[ruleId], rule.meta?.defaultOptions)` in linter.js runRules (rule-execution capsule's applyDefaultOptions flag).
**Signature:** `deepMergeArrays(defaults, userOptions): merged[]`.
**Data Shape:** arrays merge POSITIONALLY; objects merge per-key with USER-WINS; `undefined` in second means "keep first"; anything non-object (or array vs object mismatch) REPLACES outright.

### Decisive source
```js
function deepMergeObjects(first, second) {
  if (second === void 0) return first;
  if (!isObjectNotArray(first) || !isObjectNotArray(second)) return second;  // replace
  const result = { ...first, ...second };
  for (const key of Object.keys(second))
    if (Object.prototype.propertyIsEnumerable.call(first, key))
      result[key] = deepMergeObjects(first[key], second[key]);
  return result;
}
function deepMergeArrays(first, second) {
  if (!first || !second) return second || first || [];
  return [...first.map((value, i) => deepMergeObjects(value, i < second.length ? second[i] : void 0)),
          ...second.slice(first.length)];
}
```

**Flow:** zip defaults with user entries → per-index object deep-merge → append surplus user entries verbatim.
**Invariant:** `isObjectNotArray` REJECTS arrays on both sides — an array default under an array option is replaced, never element-merged (deliberate: `[["strict"]]`-style option tuples must stay atomic). `null` beats defaults (`[{a:null}] ⇒ {a:null}` — explicit null is user intent), while `undefined` preserves the default. The `propertyIsEnumerable` guard skips inherited/non-enumerable keys so prototype noise can't leak into configs. Missing user entries at trailing positions keep defaults whole. This powers `meta.defaultOptions` (rules declare sane defaults once instead of every consumer restating them).
**Probe:** `tests/lib/shared/deep-merge-arrays.js` (single parameterized `it` :120 over 35 table rows :28–118 incl. `[[{a:0}],[{a:null}]]⇒[{a:null}]`, nested-object unions, array-replacement cases, undefined-preservation).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "deepMergeArrays deepMergeObjects defaultOptions", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.shared.deep_merge_arrays.deepMergeArrays" });
```

## Verdict
Adopt for positional option merging with declared defaults; preserve the null-vs-undefined distinction and array-atomicity exactly — both encode real config-semantics decisions.
