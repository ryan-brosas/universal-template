<!-- capsule-v2 -->
# Reverse canonical resolution — how does a request path resolve to exactly one resource without false positives?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory project `ghost`. **Question:** When a URL arrives, how does the service pick the router template, query the DB minimally, and guarantee the URL is the resource's CANONICAL one rather than any path the template can pattern-match?

## resolveUrl with canonical re-check
**Path/Symbol:** `ghost/core/core/server/services/url/lazy-url-service.ts:LazyUrlService.resolveUrl` (:426–467) + `_matchesCanonicalUrl` (:474–487); matcher `ghost/core/core/server/services/url/permalink-matcher.ts:matchPermalink/toLookupParams` (:78–118); DB hook `ghost/core/core/server/services/url/lazy-find-resource.ts:createFindResource` (:74–109).
**Signature:** `async resolveUrl(urlPath: string): Promise<Resource | null>`; `matchPermalink(template: string, urlPath: string): PermalinkParams | null`; `toLookupParams(params): { id } | { slug }`.
**Data Shape:** Permalink params may carry derived segments (`year/month/day/primary_tag/primary_author`) but must capture a QUERYABLE column (`id` or `slug`); lookup cache is per-call (`Map<`${type}:${JSON.stringify(lookupParams)}`, record|null>`).

### Decisive source
```ts
// Only a URL that equals the resource's own generated (canonical) URL
// resolves, so we regenerate the record's URL for this permalink and
// confirm the captured params match it. Without this, derived/relation
// segments the query can't filter on (year/month, primary_tag) would
// resolve any slug, 200-ing a URL that has no page.
const canonicalPath = this.urlUtils.replacePermalink(config.permalink, resource);
const canonicalParams = matchPermalink(config.permalink, canonicalPath);
if (!canonicalParams) return false;
return Object.keys(captured).every((key) => canonical[key] === captured[key]);
```
**Flow:** iterate router configs in priority order → `matchPermalink` constraints: SUPPORTED_TOKENS whitelist only (`:__proto__` never matches/reaches a cache key), hyphenated multi-token segments get explicit bounds (#28076: non-last param `([^-/]+)`, last `([^/]+)`), value-format prefilter (id = 24-hex ObjectId, year = `\d{4}`, month/day = `\d{2}`), %-escape decode errors → null NOT throw, literal-only or derived-only templates never touch the DB → `toLookupParams` prefers id over slug → memoized `findResource(type, params)` → normalize record (plural→singular type + excluded-column strip) → RE-evaluate router filter against loaded record → canonical confirmation → return `{...resource, type: <plural>}`.
**Invariant:** findResource scoping mirrors the forward base filters so "a guessed slug can't surface anything a generated URL would have hidden": posts `{type:'post', status:'published'}` + tags/authors relations; pages WITHOUT relations and with primary_tag/primary_author explicitly null; TagPublic/User `visibility:public`; unknown type → null without touching models; `require:false` ⇒ miss is null not error. Post.toJSON computes primary_tag but NOT primary_author, so loadOne derives it from `authors[0]`. Relations are trimmed to `{id, slug}` — permalinks and filters read nothing else. `/news/hello/` MUST null when the record's canonical tag is podcast; `/2026/05/hello/` MUST null for an April post.
**Probe:** `ghost/core/test/unit/server/services/url/permalink-matcher.test.js` pins `"returns null for a placeholder named __proto__"`, `"does not let an earlier param consume a later one across hyphens"` (#28076), `"returns null when a date segment is not numeric"`; `lazy-url-service.test.js` pins `"returns null when the primary_tag segment is not the record canonical tag"`, `"does not repeat an identical findResource lookup within one resolveUrl call"`; `lazy-find-resource.test.js` pins `"returns null for an unknown router type without touching any model"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ghost", query: "matchPermalink resolveUrl canonical", limit: 10 });
// observed at pin: matchPermalink rank #1 (permalink-matcher.ts:78-106),
// LazyUrlService.resolveUrl rank #4 (:426-467); unrelated canonical-url helpers rank between
```

## Verdict
Adopt template-whitelist matching + format prefilter + minimal single-column lookup + filter re-check + canonical regeneration as the four-layer false-positive guard; adopt scope-mirroring in the lookup hook. Adapt token set/validators to your permalink grammar; note Ghost carries a frontend twin of the hyphen constraint at `core/frontend/services/data/match-permalink-params.js` — keep twins in lockstep if you port both sides.
