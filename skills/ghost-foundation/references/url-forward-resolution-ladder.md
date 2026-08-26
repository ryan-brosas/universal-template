<!-- capsule-v2 -->
# Forward resolution ladder — how does a resource become exactly one URL, and who wins when two routers could claim it?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory project `ghost`. **Question:** What is the ordered decision procedure from `{type, id, ...attrs}` to a public path, including the /404/ and subdirectory/absolute formatting subtleties?

## getUrlForResource ladder
**Path/Symbol:** `ghost/core/core/server/services/url/lazy-url-service.ts:LazyUrlService.getUrlForResource` (:362–401), `_recordForFilter` (:573–577), `_formatPath` (:604–612), `notFoundUrl` (:623–631); ownership twin `ownsResource` (:403–424).
**Signature:** `getUrlForResource(resource: Resource, options: UrlOptions = {}): string`; `ownsResource(routerIdentifier: string, resource: Resource | null): boolean`.
**Data Shape:** `Resource = { type: string; id: string; [k: string]: unknown }`; `UrlOptions = { absolute?: boolean; withSubdirectory?: boolean; serializerContext?... }`. Router configs iterate in REGISTRATION order, which is their priority (RouterManager mounts unsubscribe/email → preview → static routes → taxonomies → collections → static pages → apps).

### Decisive source
```ts
const record = this._recordForFilter(resource);          // plural router key → singular DB `type`
const filterRecord = this._recordForRouterFilter(record, routerType); // legacy-excluded columns stripped
if (this._hasRouterForType(routerType)) {
  const missing = this._missingBaseFields(routerType, resource);
  if (missing) return this._degradeThinResource(resource, missing, options);
  if (!this._baseFilterMatches(routerType, record)) return this.notFoundUrl(options);
}
for (const config of this.routerConfigs) {
  if (config.resourceType !== routerType) continue;
  const missing = this._missingRouterFields(config, resource, routerType);
  if (missing) return this._degradeThinResource(resource, missing, options);
  if (filterMatches(config.compiledFilter, filterRecord)) {
    const path = this.urlUtils.replacePermalink(config.permalink, resource);
    return this._formatPath(path, options);
  }
}
return this.notFoundUrl(options);
```
**Flow:** unknown/missing type ⇒ /404/ → normalize `type` for filter evaluation (`posts`→`post`) → base-filter gate ONLY when a router exists for that type (thin ⇒ degrade; failing filter e.g. draft/internal tag ⇒ /404/) → first matching router in priority order wins → permalink substitution via injected urlUtils → format. `ownsResource` mirrors base-filter + first-match so a catch-all can never claim what an earlier filtered router owns.
**Invariant:** Registration order IS priority — tests pin `featured` before default sending `/featured/hot/` vs `/meh/`. The /404/ must NOT pass createUrl's third argument: it is `trailingSlash`, `/404/` already ends in one, and a relative URL takes its subdirectory from createUrl's own base — pinned by an argument-spy test so a future "fix" trips every /404/ a subdirectory install serves.
**Probe:** `ghost/core/test/unit/server/services/url/lazy-url-service.test.js` pins `"respects router priority for filtered collections"`, `"returns /404/ for a post that fails the base filter (e.g. a draft)"`, `"builds a /404/ without passing createUrl a third argument"`, `"grants exclusive ownership to the first matching router"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ghost", query: "LazyUrlService getUrlForResource", limit: 10 });
// observed at pin: LazyUrlService.getUrlForResource rank #1 (lazy-url-service.ts:362-401),
// RouterManager.getUrlForResource delegate rank #2
```

## Verdict
Adopt the ladder shape: type gate → base gate → priority-ordered filter scan → template substitution → formatter, with a dedicated /404/ formatter aware of trailing-slash/subdirectory semantics. Adapt replacePermalink token syntax to your template engine; omit Ghost's singular/plural type mapping if your records already carry router-level types.
