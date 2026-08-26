<!-- capsule-v2 -->
# Everything-server factory — how does the canonical reference server compose capabilities, registrations, and cleanup?

**Source:** modelcontextprotocol/servers MIT `main@76d64c822f5125032f89eb71dbdb94e42b434821`; Codebase Memory `servers`. **Question:** What is the proven shape for constructing an MCP server instance so every feature registers once, conditional features wait for client capabilities, and teardown never leaks timers?

## createServer: construct-with-capabilities → register → oninitialized → cleanup closure
**Path/Symbol:** `src/everything/server/index.ts` (`createServer` :35–118; `ServerFactoryResponse` type :17–20); launcher `src/everything/index.ts` (:7–42 dynamic-import per transport); registration seams `tools/index.ts` (`registerTools` :26–39 unconditional, `registerConditionalTools` :45–55 capability-gated), `resources/index.ts`, `prompts/index.ts`, `resources/subscriptions.ts:setSubscriptionHandlers`.

**Signature:** `createServer(): ServerFactoryResponse = { server: McpServer; cleanup: (sessionId?: string) => void }`.

**Data Shape:** constructed with identity `{name: "mcp-servers/everything", title, version}` + `capabilities: {tools:{listChanged:true}, prompts:{listChanged:true}, resources:{subscribe:true,listChanged:true}, logging:{}, tasks:{...}}` + shared `instructions` string (read from a file via `readInstructions()`) + experimental task store/queue instances.

### Decisive source
```ts
// src/everything/server/index.ts:94-117 — post-init hook + teardown contract
server.server.oninitialized = async () => {
  // Register conditional tools now that client capabilities are known.
  registerConditionalTools(server);
  // Sync roots if the client supports them. Delayed until after the
  // notifications/initialized handler finishes, otherwise the request
  // gets lost.
  const sessionId = server.server.transport?.sessionId;
  initializeTimeout = setTimeout(() => syncRoots(server, sessionId), 350);
};
return {
  server,
  cleanup: (sessionId?: string) => {
    stopSimulatedLogging(sessionId);          // per-session interval maps
    stopSimulatedResourceUpdates(sessionId);
    taskStore.cleanup();                      // task-store timers
    if (initializeTimeout) clearTimeout(initializeTimeout);
  },
} satisfies ServerFactoryResponse;
```

**Flow:** factory builds McpServer with declared capabilities → `registerTools/registerResources/registerPrompts` attach every unconditional handler → `setSubscriptionHandlers` wires subscribe/unsubscribe → host transport module (stdio | sse | streamableHttp — launcher imports ONLY the requested one so unused transports never initialize) calls `server.connect(transport)` → on init, capability-dependent tools register → `cleanup(sessionId)` stops every interval/timer the session created. The HTTP host creates ONE factory instance PER SESSION and stores its cleanup for `onclose`.

**Invariant:** everything with a timer or interval created per-session must be reachable from `cleanup` — the reference server tracks simulated-logging/resource-update intervals in `Map<sessionId|undefined, Timeout>` maps precisely so teardown can sweep them (logging.ts :54–63, subscriptions.ts :143–152). Porters who fire intervals without a registry leak live timers after disconnect.

**Probe:** `src/everything/__tests__/server.test.ts` (:5–32 — returns ServerFactoryResponse, has cleanup fn, McpServer instance, oninitialized handler set, multiple servers creatable); `src/everything/__tests__/registrations.test.ts` (:20–107 — all standard tools registered; conditional tools registered only when capabilities present, NOT registered when missing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "createServer ServerFactoryResponse registerConditionalTools cleanup", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.trace_path({ project: "servers", function_name: "servers.src.everything.server.createServer", direction: "outbound", depth: 1 });
```

## Verdict
Adopt construct-capabilities-first factories, unconditional-vs-conditional registration split keyed to `oninitialized`, the always-returned cleanup closure owning every timer, and dynamic-import-per-transport launchers; adapt the capability set, instructions source, and task store to your product; omit the SSE legacy transport and simulated/demo tools unless you are building a test bench.
