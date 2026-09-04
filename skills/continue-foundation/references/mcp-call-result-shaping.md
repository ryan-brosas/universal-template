<!-- capsule-v2 -->
# MCP call-result shaping — how does a wire-format MCP response become chat context items, and what degrades instead of failing?

**Source:** continue Apache-2.0 `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does a porter map MCP `CallToolResult` content (text/resource/unknown) into conversation context without letting one bad item kill the tool call?

## isError throws; every content item becomes a ContextItem; unknown types degrade to error items
**Path/Symbol:** `core/tools/callTool.ts:87–185` (`callToolFromUri`, mcp branch).
**Signature:** internal `callToolFromUri(uri: string, args: any, extras: ToolExtras): Promise<{contextItems: ContextItem[]; mcpUiState?: McpUiState}>`.
**Data Shape:** in: decoded `[mcpId, toolName]` + coerced args; out: one ContextItem per content item (`{name: extras.tool.displayTitle, description: "Tool output" | "MCP Item Error", content: text}`) plus optional `mcpUiState {content}` from a UI resource.

### Decisive source
```ts
const response = await client.client.callTool(
  { name: toolName, arguments: coercedArgs },
  CallToolResultSchema,
  { timeout: client.options.timeout },
);
if (response.isError === true) {
  throw new Error(JSON.stringify(response.content)); // funnel converts to errorMessage
}
// per content item:
if (item.type === "text")            → { description: "Tool output", content: item.text }
else if (item.type === "resource") {
  if (item.resource?.blob)           → push "unsupported blob resource item" error item
  contextItems.push({ ..., content: item.resource.text }); // runs even for blobs — text is undefined
} else                               → `Error: tool call received unsupported item of type "${item.type}"`
```

**Flow:** connection lookup (`getConnection(mcpId)`, missing ⇒ throw "MCP connection not found") → `coerceArgsToSchema(args, tool.function.parameters)` re-stringifies deep-parsed JSON objects whose schema type is string → schema-validated wire call with the connection's own timeout → isError check → content-item mapping → optional MCP-UI extension: resourceUri read from BOTH key shapes (`mcpMeta.ui.resourceUri || mcpMeta["ui/resourceUri"]`), fetched via `client.getResource` inside try/console.error (fail-soft), only `"text"` contents become `mcpUiState`.
**Invariant:** a server's protocol-level error (`isError`) is fatal to THIS call but data to the loop (capsule tool-call-dispatch-error-funnel); a malformed CONTENT ITEM never is — it becomes an "MCP Item Error" context item that flows into the conversation. The blob branch has a latent double-push quirk: it pushes the error item and then unconditionally pushes a second item whose content is `undefined`.
**Probe:** no dedicated vitest suite for this range — coverage caveat: verified by whole-file source read + graph retrieval this pass; port with tests pinning isError⇒throw, unknown-type⇒error-item, blob⇒double-push (or fix it).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "mcp call result content shaping ui resource", limit: 10 });
```

## Verdict
Adopt per-item degradation (unknown/blob ⇒ visible error items, not exceptions) and connection-scoped timeouts on the wire call; adapt the ContextItem field mapping to your message shape; omit the MCP-UI resource branch unless your client renders server-driven UI. Trap: `isError === true` uses strict equality — servers omitting the field are treated as success.
