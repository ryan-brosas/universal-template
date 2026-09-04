<!-- capsule-v2 -->
# Anthropic wire-compat ladder — how do per-model capability flags reshape the Anthropic request without per-provider request code?

**Source:** pi-mono MIT `main@80e62761f7251a104f1b21d9c73920c720f0ec00`; Codebase Memory `pi-mono`. **Question:** How does one adapter serve first-party Anthropic and partial clones (z.ai, Kimi-anthropic, Bedrock proxies) by deriving every wire difference from a single defaulted `model.compat` record?

## Compat defaults + tool wire projection
**Path/Symbol:** `packages/ai/src/api/anthropic-messages.ts:getAnthropicCompat` (:183-196), `convertTools` (:1326-1363), beta-fallback predicate (:1323), call site in `buildParams` (:1041-1058).
**Signature:** `getAnthropicCompat(model): Required<Omit<AnthropicMessagesCompat,...>>` (defaults: `supportsEagerToolInputStreaming: true`, `supportsStrictTools: false`, `supportsCacheControlOnTools: true`, `allowEmptySignature: false`, …); `convertTools(tools, isOAuthToken, supportsEagerToolInputStreaming, supportsStrictTools, cacheControl?, deferLoading = false): Tool[]`
**Data Shape:** one `model.compat` optional record → resolved all-fields record; tools split into immediate vs deferred arrays before conversion.

### Decisive source
```ts
// line 1323 — legacy beta only when eager streaming is unsupported AND tools exist
return !!context.tools?.length && !getAnthropicCompat(model).supportsEagerToolInputStreaming;
// convertTools body:
const strict = resolveJsonSchemaStrictSampling(tool, supportsStrictTools);
const inputSchema = strict === true ? { ...(parameters as Record<string, unknown>), ...legacyInputSchema } : legacyInputSchema;
return {
    name: isOAuthToken ? toClaudeCodeName(tool.name) : tool.name,
    ...(supportsEagerToolInputStreaming ? { eager_input_streaming: true } : {}),
    ...(strict === true ? { strict: true } : {}),
    input_schema: inputSchema,
    ...(deferLoading ? { defer_loading: true } : {}),
    ...(cacheControl && index === tools.length - 1 ? { cache_control: cacheControl } : {}),
};
```

**Flow:** model declared → compat flags defaulted (`?? true/false`) → `buildParams` converts immediate tools (with cache_control when supported) then deferred tools (`defer_loading`, never cached) → per-tool: strict sampling opt-in via the tool's own `constrainedSampling` ("prefer") intersected with model support; eager streaming flag emitted per tool unless unsupported, in which case the whole request carries header `anthropic-beta: fine-grained-tool-streaming-2025-05-14` instead.
**Invariant:** every wire divergence traces to exactly one compat flag with an explicit default — no scattered `provider === "x"` branches; non-strict schemas are projected to the minimal legacy `{type:"object", properties, required}` shape so clone endpoints never see exotic JSON-Schema keywords.
**Probe:** `packages/ai/test/anthropic-eager-tool-input-compat.test.ts` (4 tests) captures real HTTP bodies against a localhost server: default sends per-tool `eager_input_streaming: true` with NO beta header; `{supportsEagerToolInputStreaming: false}` swaps it for the legacy beta header (and omits the header entirely when there are no tools); only `constrainedSampling: {type:"json_schema", strict:"prefer"}` tools get full `input_schema` + `strict: true`. Executed GREEN this pass: 4/4 passed (vitest).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-mono", query: "eager tool input partial json streaming arguments anthropic compatibility", limit: 15 });
// executed live this pass: surfaced anthropic-eager-tool-input-e2e.test helpers and the compat test fixtures;
// decisive source ranges located by named-file grep on anthropic-messages.ts (12 matches, lines 175-1356)
```

## Verdict
Adopt the defaulted-compat-record pattern and the minimal-schema projection for third-party endpoints. Adapt the specific flag set to your providers' quirks. Omit Claude Code OAuth tool-name mapping. Coverage: `no_recorded_issue` ×3 cited paths at generation 2026-08-24T16:11:21Z.
