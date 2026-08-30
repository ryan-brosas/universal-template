<!-- capsule-v2 -->
# Canonical record URLs — one builder/parser pair so search citations and fetch resolution agree

**Source:** relaticle AGPL-3.0 `main@6e3bf8df`; direct-read fallback (MCP graph absent this session). **Question:** How do you give an AI tool URLs that are both citable in chat AND resolvable back to a record — including entity types that have no per-record page?

## CanonicalRecordUrl + SearchTool/FetchTool round trip
**Path/Symbol:** `app/Support/CanonicalRecordUrl.php` (whole, 110L): `build()` (:40-54), `parse()` (:56-85), `modalQuery()` (:87-92); producers/consumers `app/Mcp/Tools/SearchTool.php` (whole, 113L), `app/Mcp/Tools/FetchTool.php` (whole, 110L).
**Signature:** `build(string $type, string $recordId, Team $team): ?string`; `parse(string $url): ?array{type: string, id: string}`; `SearchTool::handle(Request): Response|ResponseFactory`; `FetchTool::handle(Request): Response|ResponseFactory`.
**Data Shape:** Search result row: `{type, url, title, snippet(140 chars)}` wrapped as `Response::structured(['results', 'count'])`; per-entity limit default 5, max 20 (payload up to 5×limit). Fetch response: `{type, url, data}` where data is the V1 API-resource envelope.

### Decisive source
```php
// Both directions live here on purpose: the MCP search tool publishes these URLs as
// citations and the fetch tool has to resolve the same strings back to a record. When
// the two were written independently they disagreed — search emitted a tenant-less
// path that 404s in a browser, and fetch rejected the real URL a user copies from
// the address bar.
'task' => TaskResource::getUrl('index', $this->modalQuery($recordId), panel: 'app', tenant: $team),
...
if (in_array($type, self::MODAL_TYPES, true)) {          // task, note: no per-record page
    $recordId = $this->queryParam($url, 'tableActionRecord');
    return $recordId === null ? null : ['type' => $type, 'id' => $recordId];
}
```
Tasks and notes are managed from their index table, so their canonical URL is the index deep link carrying `tableAction=edit&tableActionRecord={id}` — the query that opens the record's edit modal. `parse()` strips the app-panel prefix, walks past the tenant slug to `[{tenant}, {segment}, {record?}]`, and reads modal-type ids from the QUERY param, not the path.

**Flow:** Search: per-entity `ilike` substring over name/title → policy-check each hit (`$user->cannot('view', $hit)` → skip; the model query is not team-scoped by default, the POLICY is the scope) → `build()` via Filament `Resource::getUrl(..., panel: 'app', tenant: $team)` so the URL is by construction browser-openable → null URL skips the hit. Fetch: validate full URL → parse type+id → find → policy-check view → eager-load `customFieldValues.customField.options` → return the resource envelope (internal columns like `deleted_at`/`creation_source` never leak — the resource strips them).
**Invariant:** search→fetch must compose for ALL entity types (the test fetches every URL search publishes); a URL that cannot be built must degrade to a skipped hit (`build()` try/catch → null), never crash the search; policy checks happen per hit, not per query.
**Probe:** `tests/Feature/Mcp/SearchFetchToolsTest.php` (canonical URL carries the workspace slug — "without it Filament answers 404 even for the record's owner"; fetch-every-search-URL round trip; sanitized payload without internal columns; unknown-URL and missing-record error paths).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "CanonicalRecordUrl build parse SearchTool FetchTool modalQuery", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt one builder/parser pair owned by a single class, generated through the host app's own URL generator (tenant-aware), with index-modal deep links for pageless entities. Adapt the Filament `Resource::getUrl` calls to your router. Omit the ChatGPT citation framing. Dedicated direct test suite covers the round trip.
