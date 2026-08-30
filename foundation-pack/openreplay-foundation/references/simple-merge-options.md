<!-- capsule-v2 -->
# simpleMerge deep option merge — how do user options merge with nested defaults without array clobbering surprises?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What merge semantics must option handling copy so `canvas: {fileExt}` style partials work?

## Recursive for plain objects only; arrays and null replace wholesale
**Path/Symbol:** `tracker/tracker/src/main/utils.ts` — `simpleMerge` (:317–339); consumers App constructor (`app/index.ts:327`), Sanitizer options (`sanitizer.ts:63` uses Object.assign — the SHALLOW counter-example).
**Signature:** `simpleMerge<T>(defaultObj: T, givenObj: Partial<T>): T`.
**Data Shape:** spread-copy of defaults; recursion condition `typeof === 'object' && !Array.isArray && !== null`.

### Decisive source
```ts
if (typeof userOptionValue === 'object' &&
    !Array.isArray(userOptionValue) &&
    userOptionValue !== null) {
  result[key] = simpleMerge(defaultOptionValue || {}, userOptionValue)
} else {
  result[key] = userOptionValue   // arrays & null REPLACE
}
```

**Flow:** constructor builds full default tree → merge user partial → modules each re-merge their own slice (`Object.assign(defaults, opts)` in modules is deliberately shallow for flat options).
**Invariant:** Arrays must replace, never concat (e.g. `consoleMethods`, `ignoreHeaders`). Missing defaults on the right side (`|| {}`) keep user keys even when upstream forgot to declare a default.
**Probe:** `grep -c 'simpleMerge(defaultOptionValue || {}, userOptionValue)' tracker/tracker/src/main/utils.ts` → `1`; `grep -c 'simpleMerge(defaultOptions, options)' tracker/tracker/src/main/app/index.ts` → `1`. Direct tests: none upstream (grep-pinned).
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "simpleMerge defaults options merge", limit: 10 });
```

## Verdict
Adopt object-only recursion with array replacement. Adapt typing. Omit if you use a battle-tested merge lib.
