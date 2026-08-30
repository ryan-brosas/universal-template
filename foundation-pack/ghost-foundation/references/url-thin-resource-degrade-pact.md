<!-- capsule-v2 -->
# Thin-resource degrade pact — what happens when a caller under-fetches the record it asks a URL for?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory project `ghost`. **Question:** How does URL generation survive an under-fetched record without throwing, while still making the bug findable — and what must serializers do so thin records never happen?

## Degrade-not-throw with power-of-ten reporting
**Path/Symbol:** `ghost/core/core/server/services/url/lazy-url-service.ts:LazyUrlService._degradeThinResource` (:500–539), `_missingBaseFields` (:558–569), `_missingRouterFields` (:638–677), `isPowerOfTen` (:130–136); consumer pact in `ghost/core/core/server/api/endpoints/utils/serializers/input/utils/url.js:forceUrlColumns/forceUrlRelations` (:87–141) and output `.../output/utils/url.js:forPost` (:5–85).
**Signature:** `_degradeThinResource(resource, thin: ThinResource, options): string` (returns `/404/`); `forceUrlRelations(frame, routerType): void`.
**Data Shape:** `ThinResource = { resourceType, missing: string[], baseFilter?, routerIdentifier?, filter? }`; report key = `[resourceType, routerIdentifier??'', missing.join(','), apiType:docName:method?].join('|')`; `reportedThinResources: Map<key, occurrences>`.

### Decisive source
```ts
const key = [thin.resourceType, thin.routerIdentifier ?? '', thin.missing.join(','),
  producedBy ? `${producedBy.apiType}:${producedBy.docName}:${producedBy.method}` : ''].join('|');
const occurrences = (this.reportedThinResources.get(key) ?? 0) + 1;
this.reportedThinResources.set(key, occurrences);
if (!isPowerOfTen(occurrences)) {
  return this.notFoundUrl(options);
}
logging.error(new errors.InternalServerError({ message: 'URL service could not build a URL, degraded to /404/',
  code: 'LAZY_URL_RESOLUTION_ERROR', errorDetails: { method: 'getUrlForResource', type, id, status,
  resourceKeys: Object.keys(resource), requiredRelations, occurrences, ...(producedBy ? {serializer: producedBy} : {}), ...thin } }));
```
**Flow:** record missing base-filter or router-filter columns ⇒ classify as caller bug → count per distinct cause (producer endpoint is part of the key: two endpoints under-fetching the same way are two bugs) → log at occurrence 1, then 10, 100… → return formatted /404/. Unexpected throws inside generation PROPAGATE (a backend bug must not masquerade as /404/); non-object throws rethrow unchanged. Input serializers prevent the state: force `getRequiredFields(type)` + `id` into `frame.options.columns` and `getRequiredRelations()` into `withRelated` whenever the URL will be serialized, recording `frame.forcedUrlColumns/forcedUrlRelations` for the output mapper to strip afterwards; output side skips URL building entirely when `willSerializeUrl(frame)` is false and threads `serializerContext` for the report.
**Invariant:** Thin ⇒ report + silent /404/, NEVER throw; reporting once would hide that the problem persists, per-row logging would flood — powers of ten carry "still happening, and how widely". Counters reset on `reset()` because new routing can make a resource newly fine or newly thin. The `id` column is forced even when unrequested: Bookshelf matches eager-loaded rows by parent id, and omitting it silently serializes /404/ with unattached relations.
**Probe:** `ghost/core/test/unit/server/services/url/lazy-url-service.test.js` pins `"reports each producing endpoint once, not the first one only"`, `"reports a repeated cause at each order of magnitude, not once and not per row"` (observed [1,10,100]), `"rethrows an unexpected failure rather than serving /404/"`; serializer side pinned by `ghost/core/test/unit/api/canary/utils/serializers/input/utils/url.test.js` `"records the forced columns so the output can strip them"` and `"forces the primary key so the required relations can load"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ghost", query: "thin resource degrade LAZY_URL_RESOLUTION_ERROR", limit: 10 });
// observed at pin: _degradeThinResource rank #1 (lazy-url-service.ts:500-539),
// ThinResource interface rank #2 (:89-95), createFindResource rank #7
```

## Verdict
Adopt degrade-to-NotFound with keyed occurrence counters at orders of magnitude plus rich errorDetails naming the producer; adopt the input-forces/output-strips serializer pact. Adapt the report key fields to your request telemetry; omit Ghost's specific /p/:uuid//email/:uuid/ preview fallback if your draft-preview story differs (the url service itself has no draft concept).
