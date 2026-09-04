<!-- capsule-v2 -->
# RouteInfoPathExtractor — how do global-prefix exclusions and wildcard routes compute their registered paths?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** Which exact path strings must middleware and exception handlers register for, given a RouteInfo with optional version, when the route is excluded from the prefix, or when the path IS a wildcard?

## extractPathsFrom / isAWildcard / extractNonWildcardPathsFrom / extractVersionPathFrom
**Path/Symbol:** `packages/core/middleware/route-info-path-extractor.ts:extractPathsFrom` (:30-61), `extractPathFrom` (:63-69), `isAWildcard` (:71-79), `extractNonWildcardPathsFrom` (:81-107), `extractVersionPathFrom` (:109-123).
**Signature:** `extractPathsFrom({ path, method, version }: RouteInfo): string[]`; constructor snapshots `prefixPath = stripEndSlash(addLeadingSlash(globalPrefix))` ONCE.
**Data Shape:** Returns MULTIPLE entries for wildcards because a wildcard registration must cover BOTH "everything under the prefix" AND "the prefix root itself".

### Decisive source
```ts
if (this.isAWildcard(path)) {
  const entries = versionPaths.length > 0
    ? versionPaths.map(v => [prefix + v + '$',  // bare-prefix sentinel: matches the versioned ROOT
                             prefix + v + addLeadingSlash(path)])
                .flat()
    : this.prefixPath ? [prefix + '$', prefix + addLeadingSlash(path)]
                      : [addLeadingSlash(path)];
  return Array.isArray(this.excludedGlobalPrefixRoutes)
    ? [...entries, ...excluded.map(route => ...)]   // excluded routes ALSO get raw entries appended
    : entries;
}
// non-wildcard: exclusion check FIRST (skips prefix), then prefix+version+path:
if (isRouteExcluded(this.excludedGlobalPrefixRoutes, path, method))
  return versionPaths.length ? versionPaths.map(v => v + addLeadingSlash(path))
                             : [addLeadingSlash(path)];
return versionPaths.length ? versionPaths.map(v => prefix + v + addLeadingSlash(path))
                           : [prefix + addLeadingSlash(path)];
```

**Flow:** classify wildcard (`*`, `/*`, `/*/,`, `(.*)`, or regex `^\/\{.*\}.*|^\/\*.*$`) → wildcard ⇒ emit `[prefix$, prefix+wildcard]` pairs per version (+ re-prefixed copies of every excluded-route path) → non-wildcard ⇒ exclusion gate decides prefix inclusion → version paths splice BETWEEN prefix and route path.
**Invariant:** (1) The `'$'`-suffixed entry exists because Express/Fastify wildcard patterns don't match the directory root itself — registering only `/api/*path` would miss `GET /api`. (2) Excluded-route handling differs by shape: NON-wildcard excluded routes DROP the prefix; WILDCARD registrations APPEND extra unprefixed entries for each excluded path so both worlds coexist. (3) Prefix/version composition order mirrors RoutePathFactory (prefix → version → path) — keep the two in lockstep or middleware mounts where handlers don't.
**Probe:** `packages/core/test/middleware/route-info-path-extractor.spec.ts::extractPathsFrom` (:7) + `extractPathFrom` (:96).
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "RouteInfoPathExtractor extractPathsFrom wildcard globalPrefix", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-entry wildcard registration + exclusion-aware composition whenever a router layers middleware over prefixed routes; adapt the `$` sentinel to your matcher's semantics; omit version splicing when versionless. Porting wrong: registering only the wildcard pattern (root requests fall through to 404), or letting excluded paths keep the prefix.
