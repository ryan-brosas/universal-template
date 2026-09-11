<!-- capsule-v2 -->
# MCP tool registration — how do you register 40+ agent-facing tools with uniform schemas, instrumentation, and an API-key auth lane that never grants session power?

**Source:** OpenSEO MIT `main@cd6a7820`; Codebase Memory `ext-open-seo`. **Question:** What does the tool table look like and how do API keys authenticate to /mcp without becoming Better Auth sessions?

## Typed tool registry + oseo_-scoped API-key lane
**Path/Symbol:** `src/server/mcp/server.ts:registerOpenSeoTool` (:99-126), `createOpenSeoMcpServer` (:128-203); `src/server/mcp/api-key-auth.ts:getApiKey` (:10-23), `handleMcpApiKeyRequest` (:75-140).
**Signature:** `type OpenSeoToolDefinition<Input extends ToolSchema> = { name; config: { title?; description?; inputSchema: Input; outputSchema?; annotations? }; handler: (args: ToolArgs<Input>, context: ToolContext) => CallToolResult | Promise<CallToolResult> }` where `ToolSchema = z.ZodType | z.ZodRawShape`.
**Data Shape:** 44 registered tools across projects/keywords/domain/backlinks/serp/rank-tracking/local-seo/GSC/GA4/audit/whoami. Server instructions carry the credit policy: "…ask the user for confirmation before planned batches over 2,000 credits."

### Decisive source
```ts
// Both branches require the oseo_ prefix: anything else (a Cloudflare OAuth
// access token, a stray foreign x-api-key header) falls through to the OAuth
// provider instead of being consumed here.
const headerKey = request.headers.get("x-api-key");
if (headerKey?.startsWith(API_KEY_PREFIX)) return headerKey;
// Keep API keys scoped to /mcp: verifyApiKey (rather than Better Auth's
// enableSessionForAPIKeys mock sessions) means a key never becomes a session
// that could reach account or organization endpoints.
```

**Flow:** each tool declared with raw Zod shape OR full z.object (GA4 tools), normalized to one object schema at registration → handler wrapped by `instrumentMcpToolHandler(name, outputSchema, handler)` for uniform telemetry/output validation → registration order fixed in `createOpenSeoMcpServer`. API-key path: only `oseo_`-prefixed credentials (header or Bearer) are consumed on the `/mcp` route; verified via `authApi.verifyApiKey`; keys bill the user's default hosted org; rate-limit errors map to HTTP 429 + Retry-After from `details.tryAgainIn`, other failures to 401; clientId "api_key" marks these as external MCP clients in telemetry.
**Invariant:** A non-matching credential must FALL THROUGH to the OAuth provider, never be consumed. Keys are scoped to /mcp via direct verification — they never become sessions that could reach account/org endpoints. Input schema normalization happens once at register so handlers see one shape.
**Probe:** `src/server/mcp/api-key-auth.test.ts` (prefix fall-through, 401/429 mapping); `src/server/mcp/tools/tool-text-output.test.ts` (handler output contract).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-seo", query: "registerOpenSeoTool handleMcpApiKeyRequest verifyApiKey API_KEY_PREFIX", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: declarative typed tool table + single instrumentation wrap + prefix-gated API-key lane that falls through to OAuth. Adapt schema styles and telemetry to your MCP SDK version. Omit the hosted-org defaulting if your keys bind to explicit orgs.
