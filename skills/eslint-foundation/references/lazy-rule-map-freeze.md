<!-- capsule-v2 -->
# Lazy rule map with debug instrumentation & frozen mutation surface — how does a 270-entry registry stay zero-cost until touched?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** What does the rules index actually do beyond `{name: () => require("./rule")}`, and which mutations are deliberately impossible?

## LazyLoadingRuleMap
**Path/Symbol:** `lib/rules/utils/lazy-loading-rule-map.js:LazyLoadingRuleMap` (:24–116) — constructor debug branch (:31–53), set-voiding (:55–60), lazy get/values/entries/forEach (:68–104), mutation freeze (:107–116).
**Signature:** `new LazyLoadingRuleMap(Object.entries({ "accessor-pairs": () => require("./accessor-pairs"), ... }))`.
**Data Shape:** map VALUES are loader thunks; every read method invokes-and-caches implicitly (require cache is the memo).

### Decisive source
```js
super(debug.enabled ? loaders.map(([ruleId, load]) => {
  let remaining = ...;
  return [ruleId, () => { if (!cache) { debug("Loading rule %o (remaining=%d)", ruleId, --remaining); cache = load(); } return cache; }];
}) : loaders);
// forbid mutation:
Object.defineProperty(LazyLoadingRuleMap.prototype, "set", { configurable: true, value: void 0 });
Object.defineProperties(LazyLoadingRuleMap.prototype, {
  clear: { value: void 0 }, delete: { value: void 0 },
  [Symbol.iterator]: { writable: true, value: LazyLoadingRuleMap.prototype.entries },
});
```

**Flow:** construction stores thunks untouched in the fast path → first access of each key triggers its require → iteration (`values`/`entries`/`forEach`/spread via Symbol.iterator) materializes ALL rules.
**Invariant:** the DEBUG-ONLY wrapper layer exists so `DEBUG=eslint:rules` shows a countdown ("remaining=N") without paying closure+cache cost in production — instrumentation must be free when off. Voiding `set`/`clear`/`delete` on the PROTOTYPE makes writes throw TypeError even for subclasses, guaranteeing the registry stays append-only-by-source; `Symbol.iterator` is redirected to entries so `[...rules]` yields loaded rule modules rather than thunks (a naive Map subclass leaks thunks to spread). Caching per-thunk via `let cache` guards against double-invoke during concurrent-ish access patterns.
**Probe:** coverage caveat: NO dedicated unit suite at this pin (`tests/lib/rules/utils/lazy-loading-rule-map.js` ABSENT — only indirect exercise via `tests/lib/unsupported-api.js` and rule resolution); behavior pinned by the ast-primitives capsule's prior probe claim now corrected: that path cited a nonexistent test file.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "LazyLoadingRuleMap loaders remaining", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.rules.utils.lazy_loading_rule_map.LazyLoadingRuleMap.get" });
```

## Verdict
Adopt thunk-map + prototype-frozen writes + iterator redirection for large registries; keep debug layering strictly optional. CORRECTED CLAIM: upstream has no direct test file for this class at this pin.
