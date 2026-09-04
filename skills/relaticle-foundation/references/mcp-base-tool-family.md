<!-- capsule-v2 -->
# MCP tool family — abstract base tools over an HTTP query-builder bridge

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you expose 30+ CRM tools (CRUD × 5 entities + attach/detach + search/fetch) as MCP endpoints without writing per-entity handlers?

## BaseListTool / BaseCreateTool template methods
**Path/Symbol:** `app/Mcp/Tools/BaseListTool.php` (whole, 176L): `schema()` (:49-64), `handle()` (:66-136), `buildHttpRequest()` (:138-175); `app/Mcp/Tools/BaseCreateTool.php` (whole, 75L); registration `app/Mcp/Servers/RelaticleServer.php` (:53-110).
**Signature:** abstract hooks: `actionClass()`, `resourceClass()`, `searchFilterName()`, plus optional `additionalSchema()`/`additionalFilters()`; `handle(Request $request): Response`.
**Data Shape:** List schema: search, created_after/before, filter{code:{op:val}}, sort{field,direction}, include[], per_page(15,max 100), page. Response = `{data:[...], meta:{current_page,per_page,total,last_page}}` pretty-printed.

### Decisive source
```php
$httpRequest = $this->buildHttpRequest($request);   // translate MCP args -> HTTP query semantics
...
$results = $action->execute(user:, perPage: max(1, min((int)$request->get('per_page',15),100)), page:, request: $httpRequest);
} catch (InvalidQuery $e) {
    return Response::error($e->getMessage());        // spatie/query-builder violations become tool errors
}
```
The bridge maps MCP objects onto HTTP conventions: custom-field filters nest under `filter.custom_fields`, sort becomes spatie's `-field` prefix form, `include[]` joins to a comma list — so the EXISTING HTTP API layer (actions + Spatie QueryBuilder) is reused verbatim by the AI surface.
**Flow:** token-ability gate → build synthetic HttpRequest → resolve action from container → execute with clamped pagination → resource-collection serialize → decode/re-encode round-trip (`json_decode($collection->toJson(JSON_PRETTY_PRINT))`) → attach relationship expansions via the SerializesRelatedModels map (skipping `customFieldValues`, stripping unloaded `*_count` attributes) → paginator meta appended only for LengthAwarePaginator.
**Invariant:** Clamp per_page BEFORE the action; never let InvalidQuery escape (it must degrade to a structured tool error, not a protocol failure).
**Probe:** `tests/Feature/Mcp/CompanyToolsTest.php`, `PeopleToolsTest.php`, `OpportunityToolsTest.php`, `TaskToolsTest.php`, `NoteToolsTest.php`, `SearchFetchToolsTest.php`, `ToolAnnotationsTest.php`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "BaseListTool handle buildHttpRequest schema additionalFilters", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the abstract-tool-family + HTTP-semantics bridge when exposing an existing REST domain over MCP — it kills handler duplication and keeps one filtering implementation. Adapt the specific query-builder contract. Omit the concrete entity schemas. Extensive direct-test coverage across all five entities.
