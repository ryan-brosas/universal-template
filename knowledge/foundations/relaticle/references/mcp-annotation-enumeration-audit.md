<!-- capsule-v2 -->
# Annotation enumeration audit — reflect the server's own tool registry so a new tool cannot skip the policy

**Source:** relaticle AGPL-3.0 `main@6e3bf8df`; direct-read fallback (MCP graph absent this session). **Question:** How do you guarantee every MCP tool declares the behavioral annotations (read-only / idempotent / destructive / open-world) when per-tool attributes are opt-in?

## RelaticleServer registry reflection + annotation matrix
**Path/Symbol:** `tests/Feature/Mcp/ToolAnnotationsTest.php` (whole, 70L): `annotation_matrix` dataset (:27-36), registry-enumeration test (:44-51); annotations declared on `app/Mcp/Servers/RelaticleServer.php` (:53-110) tool classes, e.g. `app/Mcp/Tools/SearchTool.php` (:27-31), `app/Mcp/Tools/WhoAmiTool.php` (:24-27).
**Signature:** `it('declares openWorldHint on every registered tool', ...)` over `(new ReflectionClass(RelaticleServer::class))->getDefaultProperties()['tools']`; per-tool `$tool->annotations(): array<string,bool>`.
**Data Shape:** Annotation matrix: list = `{readOnlyHint: true, idempotentHint: true, openWorldHint: false}`; get = readOnly+idempotent; create/update = `{openWorldHint: false}` only; delete = `{destructiveHint: true, openWorldHint: false}`; attach = idempotent (sync semantics); detach = destructive; search/fetch/whoami = readOnly+idempotent+openWorld false.

### Decisive source
```php
// The per-category matrix above only covers the classes someone remembered to list,
// which is how WhoAmiTool shipped without openWorldHint. Enumerate the server's own
// registration instead so a new tool cannot opt out of the submission policy by
// simply not being added to the dataset.
$tools = (new ReflectionClass(RelaticleServer::class))
    ->getDefaultProperties()['tools'];

foreach ($tools as $toolClass) {
    $annotations = app($toolClass)->annotations();

    expect($annotations)->toHaveKey('openWorldHint');
    expect($annotations['openWorldHint'])->toBeFalse();
}
```

**Flow:** the dataset test pins per-category semantics for representative tools → the enumeration test reflects the server class's `$tools` property (the single registration point) and asserts the safety-critical key on EVERY registered tool → a newly registered tool is covered automatically, with no test edit required.
**Invariant:** The registry property is the source of truth — enumerate IT, not a hand-maintained test list; the open-world hint must be explicitly false (closed-world CRM data), never defaulted by absence.
**Probe:** `tests/Feature/Mcp/ToolAnnotationsTest.php` (matrix + enumeration; the comment documents the real regression that motivated the second test).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "RelaticleServer tools annotations openWorldHint ToolAnnotationsTest", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt registry-reflection enumeration for any per-class metadata policy (annotations, scopes, rate-limit classes) — dataset tests drift, registration does not. Adapt the reflection target to wherever your framework registers tools. Omit the specific MCP hint vocabulary. Direct test pins both layers.
