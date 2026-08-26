<!-- capsule-v2 -->
# Resource read resolution order — exact-URI first, template scan second, one neutral not-found error for both eras

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How do you resolve a `resources/read` across static URIs and URI templates while attaching per-resource cache hints and keeping error codes era-owned?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/mcp.ts`: `resources/read` handler (:478-513), `resources/list` merge (:440-466), `registerResource` overloads + cacheHint strip (:588-657).
**Signature:** `attachCacheHintFallback(result, hint)` — rides a never-serialized carrier resolved at the encode seam.
**Data Shape:** `_registeredResources` keyed by canonical `uri.toString()`; templates matched via `uriTemplate.match(uri)` returning variables.

### Decisive source
```ts
// First check for exact resource match
const resource = this._registeredResources[uri.toString()];
if (resource) {
    if (!resource.enabled) throw new ProtocolError(InvalidParams, `Resource ${uri} disabled`);
    // A per-resource cache hint is the most specific configured author for this
    // result's 2026-07-28 cache fields; it rides a never-serialized carrier.
    return attachCacheHintFallback(await resource.readCallback(uri, ctx), resource.cacheHint);
}
// Then check templates
for (const template of Object.values(this._registeredResourceTemplates)) {
    const variables = template.resourceTemplate.uriTemplate.match(uri.toString());
    if (variables) return attachCacheHintFallback(await template.readCallback(uri, variables, ctx), template.cacheHint);
}
// Domain layer throws ONE neutral resource-not-found error; the era-aware encode seam
// (WireCodec.encodeErrorCode) selects the wire code (−32602 on every era).
throw new ResourceNotFoundError(request.params.uri);
```

**Flow:** URL parse (fail ⇒ InvalidParams with `{uri, reason:'invalid_uri'}`) → exact map hit → enabled gate → template iteration in registration order → neutral domain error. `resources/list` merges static entries with template `listCallback()` expansions, template metadata spread FIRST so per-resource metadata overrides it.

**Invariant:** Cache hints live OUTSIDE metadata (`config.cacheHint` is stripped before storage — never appears on list entries; per-resource hint wins field-by-field over the ServerOptions per-operation fallback, which itself only fills fields the result leaves unset). Error CODE selection is the encode seam's job — handlers throw semantic errors, never wire codes. Disabled resources throw rather than fall through to templates.

**Probe:** `packages/server/test/server/cacheHints.test.ts` (per-resource vs per-operation precedence, non-complete results never stamped); integration `mcp.test.ts` :2316/:2374/:2842 (resource/template remove + disable lifecycle); `eraParityErrorShapes.test.ts` (error-shape parity across eras).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "ResourceNotFoundError attachCacheHintFallback uriTemplate match registerResource", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt exact-then-template resolution + carrier-based hint attachment (never serialized into listings) + semantic-errors/era-owned-codes split; adapt URI matching to your router; omit MCP cache-field vocabulary.
