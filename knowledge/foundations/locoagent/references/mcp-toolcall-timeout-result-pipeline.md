<!-- capsule-v2 -->
# Tool-call timeout and result pipeline — how do I bound MCP tool calls, keep `_meta` on protocol errors, persist huge outputs to disk, and turn binary blobs into text blocks?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What is the full journey of an MCP tool result from wire to context window, including oversized and binary payloads?

## Race-timeout + isError-with-_meta + three-shape transform + persist-to-file ladder
**Path/Symbol:** `src/services/mcp/client.ts`: inner `callMCPTool` (:3029-3245, own timeout race :3068-3122 because SDK-internal timeouts don't fire when SSE breaks mid-request; 30s still-running progress log :3055-3066); `McpToolCallError_I_VERIFIED...carries mcpMeta` (:172-186); `processMCPResult` (:2720-2799); `transformResultContent` (:2478-2590); `persistBlobToTextBlock` (:2598-2627); `transformMCPResult` (:2662-2706); `inferCompactSchema` (:2644-2660).
**Signature:** `processMCPResult(result, tool, name): Promise<MCPToolResult>`; default tool timeout env `MCP_TOOL_TIMEOUT` else 100_000_000ms (~27.8h, :211).
**Data Shape:** transform precedence: `toolResult` field → string; `structuredContent` → JSON string + compact schema; `content[]` → per-block transform. Compact schema: arrays `[elem0]`, objects ≤10 keys at depth≤2 else `{...}`, e.g. `{title: string, items: [{id: number}]}`.

### Decisive source
```ts
// processMCPResult ordering (load-bearing):
// IDE servers ('ide') return raw content — never shown to the model directly.
// !mcpContentNeedsTruncation(content) → return as-is.
// ENABLE_MCP_LARGE_OUTPUT_FILES=false → legacy truncateMcpContentIfNeeded path.
// contentContainsImages(content) → truncate, NEVER persist:
//   "Content is guaranteed to exist..." / persisting images as JSON defeats
//   image compression logic and makes them non-viewable (:2756-2765)
// else persistToolResult(contentStr, `mcp-${server}-${tool}-${Date.now()}`) →
//   getLargeOutputInstructions(filepath, originalSize, formatDescription)
//   persist-failure → error string advising pagination tools (:2775-2784)
// binary blocks: audio/resource-blob → persistBinaryContent → "[Audio from X] saved to <path>"
// resource_link → "[Resource link: name] uri (description)" text block
```

**Flow:** callTool races its own timer → `isError:true` results THROW `McpToolCallError` carrying the first text content as message AND `_meta` (per MCP spec `_meta` is valid on error results — SDK consumers still receive it :172-186) → success passes through processMCPResult ladder → oversized non-image output lands on disk with read-back instructions instead of blowing the context.
**Invariant:** Images must take the truncation path even when file-persist is enabled; the timeout must be the caller's Promise.race (plus schema-level), not solely the SDK option; `_meta` from error results must be preserved on the thrown error.
**Probe:** `grep -n 'function inferCompactSchema' src/services/mcp/client.ts` (`2644:`) and `grep -n 'slice(0, 10)' src/services/mcp/client.ts` (`2652:`) and `grep -n 'persistBlobToTextBlock(' src/services/mcp/client.ts | head -1` (`2496:`) and `grep -n \"case 'resource_link':\" src/services/mcp/client.ts` (`2575:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "processMCPResult", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "transformResultContent", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "inferCompactSchema", limit: 5 });
```

## Verdict
Adopt the caller-side timeout race, error-result `_meta` preservation, the images-don't-persist rule, and disk-persist-with-instructions for large outputs. Adapt persistence paths and size thresholds. Omit product analytics event names.
