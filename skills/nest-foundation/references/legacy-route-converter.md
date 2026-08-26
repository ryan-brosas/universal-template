<!-- capsule-v2 -->
# LegacyRouteConverter.tryConvert — how do path-to-regexp v6 wildcards auto-upgrade to v8 syntax?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** Which legacy wildcard spellings get silently rewritten, which warn, and why does the mid-path rewrite use offset-suffixed names?

## tryConvert / printWarning / printError
**Path/Symbol:** `packages/core/router/legacy-route-converter.ts:tryConvert` (:17-74), `printWarning` (:80-87), `UNSUPPORTED_PATH_MESSAGE` (:3-4).
**Signature:** `static tryConvert(route: string, options?: { logs?: boolean }): string`.
**Data Shape:** Input: user-declared route string (leading slash optional, trailing slash optional). Output: converted route OR the original unchanged.

### Decisive source
```ts
const normalizedRoute = route.endsWith('/') ? `/${route}` : `/${route}/`;

if (normalizedRoute.endsWith('/(.*)/')) return route.replace('(.*)', '{*path}'); // silent at root '/(.*)'
if (normalizedRoute.endsWith('/*/'))    return route.replace('*', '{*path}');    // silent at root '/*'
if (normalizedRoute.endsWith('/+/'))    return route.replace('/+', '/*path');    // ALWAYS warns

// mid-path wildcards — lookahead so adjacent segments don't share one slash:
if (normalizedRoute.includes('/*/')) {
  const convertedRoute = route.replaceAll(/\/\*(?=\/)/g,
    (match, offset) => `/*path${offset}`);   // UNIQUE name per position
  printWarning(route, convertedRoute);
}
return route;
```

**Flow:** normalize to a trailing-slash form purely for classification → branch ladder: trailing regex-wildcard, trailing star, plus-repeater, mid-path stars → convert with `{*path}` / `/*path` named syntax → warn with the CONVERTED target surfaced ("Attempting to auto-convert to ...") unless `logs:false`; root catch-alls (`/`,`/(.*)`, `/*`) convert silently.
**Invariant:** (1) The mid-path replacement's lookahead `(?=\/)` is load-bearing: consuming the following slash made two adjacent `/*/*/` segments SHARE it, leaving the second star unconverted and still rejected by path-to-regexp. (2) Offset used as the name suffix guarantees uniqueness — two `path` names in one pattern are illegal; `path0/path8` style names stay stable per declaration. (3) Conversion NEVER throws — unconvertible input returns unchanged and the adapter's own error surfaces later.
**Probe:** `packages/core/test/router/legacy-route-converter.spec.ts` — trailing `(.*)`/`*` conversion + root-level silence :22/:28/:46/:52, `+`→`*path` :64, mid-path multi-segment :77, logs suppression :108.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "LegacyRouteConverter tryConvert wildcard {*path}", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt as the compat-shim pattern when a routing grammar bumps majors: classify on a NORMALIZED copy but rewrite the ORIGINAL string; adapt target syntax to your regexp engine; omit branches your grammar never accepted. Porting wrong: using one fixed name for multiple mid-path wildcards (duplicate-name crash) or warning on root catch-alls (log noise for every app).
