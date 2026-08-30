<!-- capsule-v2 -->
# Lazy required-shape inference — which columns/relations must a routable record carry before URL math is legal?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory project `ghost`. **Question:** When URLs are computed per call instead of from a boot-time cache, how does the service know what a caller's record MUST contain — and how are those requirements derived without hardcoding them?

## Derived field/relation requirements in LazyUrlService
**Path/Symbol:** `ghost/core/core/server/services/url/lazy-url-service.ts:LazyUrlService.getRequiredFields` (:290–334), `getRequiredRelations` (:259–284), module-level `BASE_FILTERS` (:75–79) and `filterScalarFields` (:160–175).
**Signature:** `getRequiredFields(routerType: string): string[]`; `getRequiredRelations(): string[]`; `filterScalarFields(filter: string | null): string[]`.
**Data Shape:** `BASE_FILTERS: Record<string, {filter: string; fields: string[]}>` — posts/pages `status:published+type:<t>` needing `[status,type]`, tags `visibility:public`; authors deliberately absent because `users.visibility` is schema-pinned to `'public'` (#10438). Requirements are memoized (`requiredRelations: string[] | null`) and invalidated by `onRouterAddedType`/`onRouterUpdated`/`reset`.

### Decisive source
```ts
const matcher = /(?:^|[+,(])\s*(\w+)(\.\w+)?:/g;
let match;
while ((match = matcher.exec(filter)) !== null) {
  const [, root, sub] = match;
  if (sub || FILTER_NON_SCALAR_FIELDS.has(root)) {
    continue;
  }
  fields.add(root);
}
```
**Flow:** router registered → cached relation set dropped → next read re-derives: relations = union over configs of tag/tags/primary_tag→`tags`, author/authors/primary_author→`authors` (from BOTH filter and permalink); fields = base-filter columns + permalink-substituted columns (`slug`, `id`, `published_at` when `:year|:month|:day` present) + computed `primary_tag`/`primary_author` forced like scalar columns (the model only attaches them when `options.columns` names them) + scalar columns referenced by filters.
**Invariant:** Only field names at an NQL expression boundary (start or after `+`/`,`/`(`) count — colon-bearing VALUES such as `published_at:>'2020-01-01T00:00:00Z'` must yield `published_at`, never `00`. Dotted clauses (`tags.visibility`) are relation sub-fields, not scalar columns; `page`/`type` discriminators go through the type transformer, not the required-columns list; excluded legacy columns (see `url-filter-eval-compat`) are never required.
**Probe:** `ghost/core/test/unit/server/services/url/lazy-url-service.test.js` pins `"does not capture colon-bearing filter values (timestamps, URLs) as fields"` and `"requires primary_tag/primary_author when a router filter references them"`; also `"returns [] for a type with no base filter (incl. authors — visibility is vestigial)"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ghost", query: "getRequiredFields getRequiredRelations", limit: 10 });
// observed at pin: LazyUrlService.getRequiredFields rank #1 (lazy-url-service.ts:290-334),
// getRequiredRelations rank #4 (:259-284)
```

## Verdict
Adopt derive-requirements-from-config-on-demand with boundary-anchored field extraction and memoize-until-config-changes; adopt forcing computed attributes (`primary_*`) as if scalar. Adapt the BASE_FILTERS table to your model states; omit Ghost's schema-pinned author visibility rationale if your users table has real visibility values.
