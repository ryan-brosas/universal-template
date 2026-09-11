<!-- capsule-v2 -->
# llms.txt agent index — how do you publish an always-fresh machine-discoverable docs index without making it an SEO surface?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** How is `/llms.txt` generated so it cannot drift from the pages it lists, and what content rules keep it useful to agents rather than search engines?

## HelpController::llmsTxt built from the same manifests the pages render from
**Path/Symbol:** `packages/Documentation/src/Http/Controllers/HelpController.php` :88 `llmsTxt(): Response`, :111 `llmsTxtBody()`, section builders :157-282.
**Signature:** `llmsTxt(): Response` — plain `text/plain; charset=UTF-8`, 200; entries are sprintf lines `- [%s](%s): %s` (title/link/description).
**Data Shape:** Sections in fixed order: Help Centre → Developer Documentation → Product → Comparisons & Alternatives → Company (always present) → Blog (only if route exists). Empty sections OMITTED entirely (`if ($help !== [])` guards), never empty headers.

### Decisive source
```php
/**
 * A plain, accurate index for agent discovery -- generated from the same
 * manifests the pages themselves render from, so it can't drift out of
 * date. Never a ranking mechanism: Google doesn't read llms.txt.
 */
public function llmsTxt(): Response
```
(:83-88). Freshness mechanism: Help entries iterate `$this->repository->categories()` + `pagesIn()` (:244-260); Docs entries iterate `pagesIn('docs/guides')` plus a config-sourced API-reference entry (:263-282); blog entries query published posts via `toBase()->get(['title','slug','excerpt'])` (:225-229). Feature-aware degradation: `Route::has('blog.index')` gate (:214) keeps a disabled-blog deployment from emitting dead links.

**Flow:** request → assemble from live repositories/config/routes → fixed-section plain-text response. The same controller also serves the human help hub (:37) and markdown variants — one source of truth, three renderings.
**Invariant:** Generated-from-manifests means zero manual maintenance and zero drift; every emitted URL must come from `route()` lookups (which throw on missing routes) or be gated by `Route::has()`.
**Probe:** `tests/Smoke/RouteTest.php` (route registration); coverage caveat: no dedicated direct test asserts body contents at this pin — pinned via controller source + route smoke test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "llmsTxt llmsTxtBody llmsTxtHelpEntries llmsTxtDocsEntries", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt generate-don't-maintain for llms.txt with Route::has-gated sections; adapt section taxonomy; omit Relaticle's CompetitorFacts comparison copy. Direct coverage is smoke-level only — stated honestly.
