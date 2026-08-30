<!-- capsule-v2 -->
# Tool-call dispatch error funnel — how does a tool call execute without ever rejecting into the agent loop?

**Source:** continue Apache-2.0 `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** Where do tool calls actually EXECUTE, and what failure shape does the agent loop receive when a tool throws, times out, or returns garbage?

## callTool → URI fork → built-in switch, catch-all to error result
**Path/Symbol:** `core/tools/callTool.ts` whole (280 lines): `callTool` (:235–280), `callToolFromUri` (:67–185), `callBuiltInTool` (:187–230).
**Signature:** `callTool(tool: Tool, toolCall: ToolCall, extras: ToolExtras): Promise<{contextItems: ContextItem[]; errorMessage: string | undefined; errorReason?: ContinueErrorReason; mcpUiState?: McpUiState}>`.
**Data Shape:** success = populated contextItems + `errorMessage: undefined`; ANY failure = empty contextItems + string message (+ typed reason only for `ContinueError`). Never rejects.

### Decisive source
```ts
// Handles calls for core/non-client tools
// Returns an error context item if the tool call fails
// Note: Edit tool is handled on client
export async function callTool(tool, toolCall, extras) {
  try {
    const args = safeParseToolCallArgs(toolCall);
    const { contextItems } = tool.uri
      ? await callToolFromUri(tool.uri, args, extras)
      : { contextItems: await callBuiltInTool(tool.function.name, args, extras) };
    if (tool.faviconUrl) contextItems.forEach((item) => { item.icon = tool.faviconUrl; });
    return { contextItems, errorMessage: undefined };
  } catch (e) {
    let errorMessage = `${e}`;
    let errorReason;
    if (e instanceof ContinueError) { errorMessage = e.message; errorReason = e.reason; }
    else if (e instanceof Error) { errorMessage = e.message; }
    return { contextItems: [], errorMessage, errorReason };
  }
}
```

**Flow:** parse args (see tool-args-parse-coerce.md) → fork on `tool.uri`: set ⇒ protocol dispatch (`http:`/`https:` ⇒ POST `{arguments}` JSON and return `data.output`; `mcp:` ⇒ manager connection + schema-coerced wire call; anything else ⇒ throw `Unsupported protocol`) — unset ⇒ 17-case switch dispatching to `readFileImpl`…`viewSubdirectoryImpl`, unknown name throws ``Tool "<name>" not found`` → on success stamp `tool.faviconUrl` onto EVERY returned item (overrides per-item icons) → any throw anywhere lands in the funnel.
**Invariant:** a tool failure is DATA, not an exception — the agent loop can render it as an assistant-visible error and continue; only `ContinueError` preserves machine-readable `errorReason`. The edit-family tools never reach this dispatcher (client-executed by design).
**Probe:** no dedicated vitest suite exists for this file — coverage caveat: verified by whole-file source read + graph retrieval this pass; port with a funnel unit test (throwing impl ⇒ `{contextItems: [], errorMessage}` shape).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "callTool built-in dispatch error funnel", limit: 10 });
```

## Verdict
Adopt the never-reject funnel returning `{contextItems, errorMessage, errorReason}` and the uri-vs-name dispatch split; adapt the built-in switch to your tool registry; omit the http-URI tool plane if you have no remote-function tools. Trap: the faviconUrl post-stamp mutates returned items — if your ContextItem type freezes icons elsewhere, clone before stamping.
