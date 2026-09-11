<!-- capsule-v2 -->
# NQL filter evaluation + legacy exclusion contract — how do routes.yaml filters decide membership without silently changing old routing?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory project `ghost`. **Question:** Where is the single place a collection filter is evaluated, what happens on a malformed filter, and why are whole columns stripped before matching?

## Centralized NQL evaluation in router-filter.ts
**Path/Symbol:** `ghost/core/core/server/services/url/router-filter.ts:buildFilter` (:47–52), `filterMatches` (:63–77), `EXPANSIONS` (:7–14), `PAGE_TRANSFORMER` (:16–22); companion `ghost/core/core/server/services/url/config.js` (exclude lists) consumed by `lazy-url-service.ts:buildExcludedFilterFields` (:116–125) + `_recordForRouterFilter` (:587–602).
**Signature:** `buildFilter(filter: string | null): CompiledFilter | null`; `filterMatches(compiledFilter: CompiledFilter | null, record: Record<string, unknown>): boolean`.
**Data Shape:** One compiled matcher per router config; `null` filter always matches. Expansions rewrite shorthand (`author`→`authors.slug`, `tag`/`tags`→`tags.slug`, `primary_tag`→`primary_tag.slug`, …); page transformer rewrites legacy `page:false`→`type:post`, `page:true`→`type:page`.

### Decisive source
```ts
// A null filter always matches; anything that throws is a non-match, not an error.
//
// That covers malformed filters as well as odd records, because NQL parses
// lazily: `buildFilter` returns happily for a filter like `((`, and the parse
// error surfaces here on the first `queryJSON`. So this catch is the only
// thing standing between a bad routes.yaml filter and a site that cannot
// route — do not narrow it on the assumption that compilation already
// failed somewhere upstream.
try {
  return !!compiledFilter.queryJSON(record);
} catch (err) {
  logging.warn('NQL match failed', ...);
  return false;
}
```
**Flow:** compile at registration (no parse) → at match time evaluate against a REDUCED record: `_recordForRouterFilter` strips the per-type `exclude` columns from services/url/config.js so they read as ABSENT (NQL: absent = null) — while the BASE filter runs against the full record because it reads status/type/visibility.
**Invariant:** Malformed filters (`((`, `+++`, `foo:[unclosed`) must COMPILE without throwing and evaluate to non-match with one warn — the lazy-parse catch is the sole guard keeping a bad routes.yaml from taking down all routing. Legacy parity: the old engine cached rows without these columns, so `custom_template:null` matched everything; the new engine loads real values and MUST strip them before router-filter evaluation or posts with custom templates stop routing. Excluded fields are never required/force-loaded (a resource lacking one matches null, not thin).
**Probe:** `ghost/core/test/unit/server/services/url/router-filter.test.js` pins `"a malformed filter cannot take routing down"` (three malformed filters → non-match + warn) and `"transforms page:false to type:post"`; `ghost/core/test/unit/server/services/url/lazy-url-service.test.js` pins `"matches a filter on an excluded column as absent (→ null)"`, `"does not treat a resource lacking an excluded filter column as thin"`, `"does not force-load excluded columns as required fields"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ghost", query: "filterMatches buildFilter nql router filter", limit: 10 });
// observed at pin: buildFilter/filterMatches rank #1-#2 (router-filter.ts:47-52, 63-77),
// _recordForRouterFilter rank #9 (lazy-url-service.ts:587-602)
```

## Verdict
Adopt one shared evaluator for forward lookup, ownership and reverse lookup ("decide membership the same way"), fail-open-to-non-match on evaluation errors, and strip-then-match for columns your predecessor cached without. Adapt expansion keys/transformer to your filter grammar; omit the specific exclude lists (they encode Ghost's own history).
