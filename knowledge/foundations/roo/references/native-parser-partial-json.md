<!-- capsule-v2 -->
# Partial-JSON streaming preview — how do you show live tool arguments before the JSON closes?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How do you parse an accumulating JSON argument string chunk-by-chunk so the UI gets partial parameter values immediately, without corrupting state or breaking on malformed prefixes?

## Accumulator + partial-json per chunk, MCP calls excluded
**Path/Symbol:** `src/core/assistant-message/NativeToolCallParser.ts` (`processStreamingChunk` :250-287, `startStreamingToolCall` :220-231, `finalizeStreamingToolCall` :294-311; static `streamingToolCalls: Map<string, {id, name, argumentsAccumulator}>` :56-64).
**Signature:** `startStreamingToolCall(id: string, name: string): void`; `processStreamingChunk(id: string, chunk: string): ToolUse | null`; `finalizeStreamingToolCall(id: string): ToolUse | McpToolUse | null`.
**Data Shape:** Per-id accumulator of raw JSON text. Partial result is a `ToolUse` with `partial: true`, `params` stringified for display AND a per-tool typed `nativeArgs` built from whatever keys parsed so far.

### Decisive source
```ts
toolCall.argumentsAccumulator += chunk
// Dynamic MCP tools: NO partial updates — wait for final (name carries server/tool identity)
const mcpPrefix = MCP_TOOL_PREFIX + MCP_TOOL_SEPARATOR
if (toolCall.name.startsWith(mcpPrefix)) return null

try {
    const partialArgs = parseJSON(toolCall.argumentsAccumulator)   // partial-json
    const resolvedName = resolveToolAlias(toolCall.name) as ToolName
    return this.createPartialToolUse(toolCall.id, resolvedName,
        partialArgs || {}, true,
        toolCall.name !== resolvedName ? toolCall.name : undefined) // alias → originalName kept
} catch {
    return null // severely malformed prefix: skip THIS update, keep accumulating
}
```
Finalize runs `parseToolCall` on the complete accumulator (fail-fast path), then **deletes the id's entry** — finalize is one-shot. `clearAllStreamingToolCalls()` clears everything at new-request start.

**Flow:** start registers {id, name} with empty accumulator → each delta appends and re-parses the WHOLE accumulated string via partial-json (`parseJSON`) → UI receives fresh partial ToolUse each chunk → finalize parses complete JSON once, cleans up, returns final ToolUse/McpToolUse.
**Invariant:** Every chunk re-parses from scratch (no incremental JSON state to corrupt); a failed partial parse yields `null`, never throws and never mutates the accumulator backward; MCP-named calls never emit partials (their name is only fully known at end); finalize deletes its state so a late duplicate chunk cannot double-finalize.
**Probe:** `src/core/assistant-message/__tests__/NativeToolCallParser.spec.ts:298` ("should emit a partial ToolUse with nativeArgs.path during streaming"), :318 ("should parse read_file args on finalize").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "processStreamingChunk argumentsAccumulator partial json", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt accumulate-and-reparse via partial-json + null-on-malformed + MCP-partial-suppression. Adapt the ToolUse shape. Omit nothing: suppressing partials for dynamic-name tools and deleting state at finalize are correctness properties, not optimizations.
