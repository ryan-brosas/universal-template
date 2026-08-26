<!-- capsule-v2 -->
# RoutePathFactory.create — in what order do version, module, controller, method, and global prefix concatenate?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What is the exact path-assembly pipeline (and its slash normalization) that turns decorator fragments into registered route paths?

## create / getVersion / appendToAllIfDefined / isExcludedFromGlobalPrefix
**Path/Symbol:** `packages/core/router/route-path-factory.ts:create` (:21-78), `getVersion` (:80-84), `getVersionPrefix` (:86-96), `appendToAllIfDefined` (:98-115), `isExcludedFromGlobalPrefix` (:117-144), `truncateVersionPrefixFromPath` (:146-169).
**Signature:** `create(metadata: RoutePathMetadata, requestMethod?: RequestMethod): string[]` — returns MULTIPLE paths because versions and fragments can be arrays.
**Data Shape:** metadata `{ versioningOptions?, modulePath?, ctrlPath?, methodPath?, globalPrefix?, controllerVersion?, methodVersion? }`; `VersionValue = VERSION_NEUTRAL | string | string[]`.

### Decisive source
```ts
let paths = [''];
// 1. URI version fan-out FIRST (methodVersion overrides controllerVersion):
paths = flatten(paths.map(p => versions.map(v =>
  v === VERSION_NEUTRAL ? p : `${p}/${versionPrefix}${v}`)));
// 2-4. module → ctrl → method, each: stripEndSlash(acc) + addLeadingSlash(fragment)
const concatPaths = (a, b) => stripEndSlash(a) + addLeadingSlash(b);
// 5. global prefix LAST, with per-route exclusion:
if (metadata.globalPrefix) paths = paths.map(path =>
  this.isExcludedFromGlobalPrefix(path, requestMethod, ...) ? path
    : stripEndSlash(metadata.globalPrefix || '') + path);
// 6. final normalization — leading slash always, trailing slash stripped:
return paths.map(p => addLeadingSlash(p || '/'))
            .map(p => (p !== '/' ? stripEndSlash(p) : p));
```

**Flow:** start from `['']` → URI-version prefix injection (`v` default; `prefix:false ⇒ ''`, custom prefix honored) → cartesian product through `appendToAllIfDefined` for modulePath/ctrlPath/methodPath (arrays multiply) → global-prefix prepend with exclusion check → normalize edges.
**Invariant:** (1) Order is fixed: version INSIDE module/controller/method but OUTSIDE global prefix — a ported router that appends the global prefix first produces `/api/v1/...` vs the correct `/v1/api/...` inversion for excluded routes. (2) Exclusion matching happens against the path with the version prefix TRUNCATED back off (`truncateVersionPrefixFromPath`) and only when `requestMethod` is provided (log-only calls pass undefined ⇒ never excluded). (3) `VERSION_NEUTRAL` emits NO segment yet still matches header/media-type versioning downstream. (4) Empty fragment `''` normalizes to `'/'`, never to empty string.
**Probe:** `packages/core/test/router/route-path-factory.spec.ts::create` ("valid, concatenated paths (various combinations)" :16 — one mega-table) + `isExcludedFromGlobalPrefix` :230-318 + `getVersionPrefix` :319-356.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "RoutePathFactory create appendToAllIfDefined globalPrefix version", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the six-stage order as the canonical route-composition contract (it is what makes `exclude` patterns stable); adapt prefix/slash conventions to your adapter; omit URI-version stages when versionless. Porting wrong: concatenating without stripEndSlash+addLeadingSlash pairing (double or missing slashes), or applying global prefix before version segments.
