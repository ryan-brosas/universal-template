<!-- capsule-v2 -->
# In-process MCP server — when a local MCP server would cost a ~325MB subprocess, how do you serve it over a linked in-memory transport pair?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you intercept one named stdio MCP server and run it inside the CLI process without the rest of the MCP stack noticing?

## in-process-mcp-server
**Path/Symbol:** `src/services/mcp/client.ts:905-925` (transport selection), `src/utils/claudeInChrome/mcpServer.ts` (`createChromeContext` :85-246, `runClaudeInChromeMcpServer` :248-275), `src/services/mcp/InProcessTransport.js` (`createLinkedTransportPair`).
**Signature:** transport branch: `serverRef.type === 'stdio' && isClaudeInChromeMCPServer(name)` → build context, `createClaudeForChromeMcpServer(context)`, `connect(serverTransport)`, hand `clientTransport` to the normal client flow. Name test is normalization-based: `normalizeNameForMCP(name) === 'claude-in-chrome'`.
**Data Shape:** `ClaudeForChromeContext = {serverName, logger, socketPath, getSocketPaths, clientTypeId, onAuthenticationError, onToolCallDisconnected, onExtensionPaired, getPersistedDeviceId, bridgeConfig?, initialPermissionMode?, callAnthropicMessages?, trackEvent}`.

### Decisive source
```ts
// Run the Chrome MCP server in-process to avoid spawning a ~325 MB subprocess
const { createChromeContext } = await import('../../utils/claudeInChrome/mcpServer.js')
const { createClaudeForChromeMcpServer } = await import('@ant/claude-for-chrome-mcp')
const { createLinkedTransportPair } = await import('./InProcessTransport.js')
inProcessServer = createClaudeForChromeMcpServer(context)
const [clientTransport, serverTransport] = createLinkedTransportPair()
await inProcessServer.connect(serverTransport)
transport = clientTransport
```
plus lazy UI import at :234-237:
```ts
// Lazy: toolRendering.tsx pulls React/ink; only needed when Claude-in-Chrome MCP server is connected
```

**Flow:** reserved-name check in mcp/config.ts (:636-637) BLOCKS users from defining their own `claude-in-chrome` server; client.ts diverts that name to the in-process path BEFORE generic stdio spawn; everything downstream (tool listing, permissions, calls) sees an ordinary MCP server. The SAME context factory serves both this path and the standalone subprocess mode entered via `cli.tsx --claude-in-chrome-mcp` argv dispatch.
**Invariant:** interception happens by NAME at the transport-choice layer (after proxy/HTTP branches), so config validation must reserve the name first or user configs would silently hijack it; heavy React/ink render modules stay behind lazy require keyed on the same predicate — a headless embed never loads them.
**Probe:** no upstream test. Deterministic pins: `grep -n "325 MB" src/services/mcp/client.ts` → :909; `grep -n "Block reserved server name" src/services/mcp/config.ts` → :636.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "isClaudeInChromeMCPServer createLinkedTransportPair", limit: 10 });
```

## Verdict
Adopt name-keyed in-process interception with linked transports for heavyweight first-party MCP servers. Adapt which servers qualify. Omit Computer-Use twin details (same pattern, separate gate). Coverage caveat: no unit tests upstream.
