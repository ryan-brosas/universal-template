<!-- capsule-v2 -->
# Suspension-inside-MCP-handler — how do I suspend a host tool call inside a remote agent loop without polling?

**Source:** pi-factory-droid MIT `master@e0a53248ab173b6f0ff763441c1f1160bedd016e`; Codebase Memory `pi-factory-droid`. **Question:** How can a host execute tools for a remote agent when the host only speaks request/response, given the agent's tool loop expects a synchronous result?

## Register each host tool as a foreign-agent tool whose handler awaits a promise
**Path/Symbol:** `src/pi-tools-bridge.ts:buildPiToolsMcpServer` (180-203), `bridgedToDroidResult` (205-213).
**Signature:** `buildPiToolsMcpServer(tools: Tool[], board: PiToolsBridgeBoard): SdkMcpServer` — handler `async () => bridgedToDroidResult(await board.waitForPiResult(name))`.
**Data Shape:** Each Pi `Tool {name, description, parameters}` becomes one Droid SDK MCP tool under server name `PI_TOOLS_MCP_SERVER = "pi-tools"`; parameters are converted via `jsonSchemaToZodShape` — an empty shape registers the parameterless `droidTool` overload.

### Decisive source
```ts
export function buildPiToolsMcpServer(tools: Tool[], board: PiToolsBridgeBoard): SdkMcpServer {
  board.registerNameMaps(tools);
  const mcpTools = tools.map((t) => {
    const name = sanitizeToolName(t.name);
    const shape = jsonSchemaToZodShape(t.parameters);
    const hasShape = Object.keys(shape).length > 0;
    if (hasShape) {
      return droidTool(name, t.description || t.name, shape, async () => {
        const result = await board.waitForPiResult(name);   // suspends HERE
        return bridgedToDroidResult(result);
      });
    }
    return droidTool(name, t.description || t.name, async () => {
      const result = await board.waitForPiResult(name);
      return bridgedToDroidResult(result);
    });
  });
  return createSdkMcpServer({ name: PI_TOOLS_MCP_SERVER, version: "1.0.0", tools: mcpTools });
}
```

Empty-content guard at the wire boundary:
```ts
function bridgedToDroidResult(result: BridgedToolResult) {
  return {
    content: result.content.length ? result.content : [{ type: "text", text: "" }],
    ...(result.isError ? { isError: true } : {}),
  };
}
```

**Flow:** pool-entry creation (`getOrCreateEntry`, providers.ts:694-709) builds the board + MCP server and attaches it via `createSession({..., mcpServers: [mcpServer]})` → Droid calls the tool → Droid's own agent loop invokes the MCP handler → the handler's promise stays pending until the HOST's next `streamSimple` call delivers results through the board → handler resolves with `{content, isError?}` and Droid's loop continues with that output.
**Invariant:** The handler never polls and never opens a second channel — suspension is just an unresolved promise closed over the shared board, so it survives across streamSimple requests on the SAME pooled session. Content arrays must be non-empty (`[{type:"text",text:""}]` fallback) because the transport rejects empty content. `isError` is spread conditionally so success results carry no error field.
**Probe:** `test/pi-tools-bridge.test.ts:29-54` drives the handler-side promise (`waitForPiResult`) to resolution through both race orderings — the same await path the registered handler uses. No end-to-end subprocess test exists (recorded caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-factory-droid", query: "buildPiToolsMcpServer createSdkMcpServer droidTool waitForPiResult bridgedToDroidResult", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt "tool handler = awaited promise over a shared rendezvous object" whenever a request/response host must serve a long-lived agent loop; it needs no polling, sockets, or queue workers. Adapt the registration API (`droidTool`/`createSdkMcpServer`) to your agent's plugin surface. Omit the Droid SDK types and the pi-tools server-name constant.
