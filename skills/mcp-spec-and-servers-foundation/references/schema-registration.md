<!-- capsule-v2 -->
# Tool/Prompt/Resource wire schemas — what exact shape must registration and list/call payloads have?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b`; Codebase Memory `modelcontextprotocol`. **Question:** What are the canonical `Tool`, `Prompt`, and `Resource` structures, the CallToolResult success-vs-error split, and the pagination/caching envelope every list result shares?

## Registration shapes, isError semantics, cursor + ttl envelope
**Path/Symbol:** `schema/draft/schema.ts` — `Tool` :1973–2015 (`name`/`title?` via BaseMetadata :954+, `description?`, `inputSchema: {$schema?, type: "object", ...}` REQUIRED root object, `outputSchema?`, `annotations?: ToolAnnotations` :1912–1950 hints with defaults, `_meta?`); `CallToolResult` :1809–1838 (`content: ContentBlock[]`, `structuredContent?: unknown`, `isError?: boolean`); `CallToolRequestParams` :1863–1872 (`name`, `arguments?`); `Prompt`/`PromptArgument` :1659–1692; `Resource`/`ResourceTemplate` :1441+; `ResourceContents` text/blob variants :1514–1548.

### Decisive source
```ts
// schema/draft/schema.ts:1823-1837 — the error-routing invariant, verbatim:
//   Whether the tool call ended in an error.
//   If not set, this is assumed to be false (the call was successful).
//   Any errors that originate from the tool SHOULD be reported inside the
//   result object, with isError set to true, _not_ as an MCP protocol-level
//   error response. Otherwise, the LLM would not be able to see that an
//   error occurred and self-correct.
//   However, any errors in finding the tool, an error indicating that the
//   server does not support tool calls, or any other exceptional conditions,
//   should be reported as an MCP error response.
isError?: boolean;
```
`inputSchema` rules (:1982–1995): arguments are always objects so `type: "object"` is required at the root; any JSON Schema 2020-12 keyword may appear alongside (`oneOf/allOf/if/$ref/$defs`) — 2020-12 is the default dialect when `$schema` is absent (basic/index.mdx :251–258); `$ref` to network URIs MUST NOT be auto-dereferenced (basic/index.mdx :299–310); validators SHOULD bound schema depth/subschema count against DoS (:312–318).

**Shared list envelope** (:1054–1110): every `*/list` request takes opaque `cursor?`; every result returns `nextCursor?` only when more pages exist (pagination.mdx: opaque tokens, clients MUST NOT guess). List/read/discover results also carry `ttlMs: number` + `cacheScope: "public"|"private"` (`CacheableResult`) — HTTP-Cache-Control-like freshness hints where `0` means re-fetch each time and `private` forbids cross-auth-context cache sharing. `tools/list_changed|prompts/list_changed|resources/list_changed` notifications exist per family but deliver ONLY on opted-in listen streams (:1888–1898).

**Content blocks** (:2305+): `text|image|audio|resource_link|embedded_resource`; prompts return `PromptMessage{role: "user"|"assistant", content}` (:1704+); `ToolAnnotations` are HINTS — title, readOnlyHint (default false), destructiveHint (default true), idempotentHint, openWorldHint — never trusted for security decisions from untrusted servers (:1903–1908).

**Invariant:** domain failures travel INSIDE a successful response flagged `isError: true` so the model can see and self-correct; protocol failures (unknown tool, unsupported method) are JSON-RPC errors. Porters who raise protocol errors for tool-internal failures blind the LLM. And any structured output must satisfy the declared `outputSchema` if present.

**Probe:** no runtime tests in the spec repo; machine-checkable anchors are the TS types themselves plus `scripts/generate-schemas.ts` → `schema.json` and `scripts/validate-examples.ts` over `schema/draft/examples/{ListToolsResult,CallToolResult}/**`. Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:** (`query` BM25 now zero-hits this doc-shaped graph — noise-label filtering; use `name_pattern`; bare `Tool` alone is too broad at 50+ rows):
```bash
codebase-memory-mcp cli search_graph --project modelcontextprotocol \
  --name-pattern 'inputSchema|CallToolResult|ToolAnnotations' --limit 15
```

## Verdict
Adopt the Tool/Prompt/Resource registration shapes, object-root inputSchema with 2020-12 default dialect, isError-inside-result routing, opaque-cursor pagination, and ttlMs/cacheScope caching hints; adapt your tool catalog, annotation truthfulness, and content types to host needs; omit icon rendering and audio blocks until a target UI requires them.
