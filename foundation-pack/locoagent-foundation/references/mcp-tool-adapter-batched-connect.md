<!-- capsule-v2 -->
# Tool-annotation-to-Tool adapter and batched connection fan-out — how do MCP tools become first-class host tools, and how do 50 servers connect without process-storm?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How do I map MCP `tools/list` onto my internal Tool interface (annotations, permissions, concurrency) and connect local vs remote servers at different concurrency ceilings?

## fetchToolsForClient mapping + split pMap batches
**Path/Symbol:** `src/services/mcp/client.ts`: `fetchToolsForClient` (:1743-1998, LRU-capped memoize keyed by client NAME, size `MCP_FETCH_CACHE_SIZE = 20` :1726); annotation mapping (:1795-1812); permission passthrough with allow-rule suggestion (:1814-1832); skip-prefix mode (:1760-1774); IDE tool filter `isIncludedMcpTool`/`ALLOWED_IDE_TOOLS` (:567-573); batching `processBatched` via pMap (:2212-2224), partitioners `getMcpServerConnectionBatchSize` default **3** / `getRemoteMcpServerConnectionBatchSize` default **20** (:552-561), `isLocalMcpServer` (:563-565); parallel groups (:2388-2402).
**Signature:** `memoizeWithLRU(async (client: MCPServerConnection): Promise<Tool[]>, client => client.name, 20)`; `processBatched(items, concurrency, processor)` = `pMap(items, processor, {concurrency})`.
**Data Shape:** annotations consumed: `readOnlyHint → isConcurrencySafe() AND isReadOnly()`; `destructiveHint → isDestructive()`; `openWorldHint → isOpenWorld()`; `title → userFacingName`; `_meta['anthropic/searchHint']` whitespace-collapsed (a raw newline would inject orphan lines into the deferred-tool list :1776-1784); `_meta['anthropic/alwaysLoad'] === true`.

### Decisive source
```ts
// Replaced 2026-03: previous implementation ran fixed-size sequential batches
// (await batch 1 fully, then start batch 2). That meant one slow server in
// batch N held up ALL servers in batch N+1... pMap frees each slot as soon as
// its server completes. Same concurrency ceiling, same results, better scheduling.
await Promise.all([
  processBatched(localServers, getMcpServerConnectionBatchSize(), processServer),
  processBatched(remoteServers, getRemoteMcpServerConnectionBatchSize(), processServer),
])
// tool.call(): ensureConnectedClient(client) FIRST, then callMCPToolWithUrlElicitationRetry;
// progress events mcp_progress started/completed/failed carry {serverName, toolName, elapsedTimeMs}
// error wrapping: plain Error → TelemetrySafeError(message, message.slice(0,200));
//   McpError with numeric code → TelemetrySafeError(message, `McpError ${code}`)
```

**Flow:** per connected server fetch tools/resources/prompts in one `Promise.all` (skills only when resources capability present :2344-2356) → map each MCP tool to a full Tool (name `mcp__<server>__<tool>` unless SDK no-prefix mode lets MCP override builtins while mcpInfo keeps permission identity) → resource-capable servers contribute the shared ListMcpResources/ReadMcpResource tools exactly ONCE fleet-wide (`resourceToolsAdded` latch :2360-2364).
**Invariant:** Local (stdio/sdk) and remote servers MUST run as two concurrent pMap groups — spawning processes at network concurrency storms the machine; a single slow server must occupy ONE slot, not block a batch boundary. Fetch caches are keyed by server name so reconnects reuse them only after onclose deletes them.
**Probe:** `grep -n 'MCP_FETCH_CACHE_SIZE = 20' src/services/mcp/client.ts` (`1726:`) and `grep -n \"parseInt(process.env.MCP_SERVER_CONNECTION_BATCH_SIZE || '', 10) || 3\" src/services/mcp/client.ts` (`553:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "MCPTool call", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "memoized tool fetch cache LRU server name", limit: 5 });
```

## Verdict
Adopt annotation→capability mapping, passthrough-permission-with-suggestion, two-tier pMap batching, and once-only shared resource tools. Adapt names/prefix scheme to your host's naming rules. Omit IDE allowlist and Chrome/ComputerUse overrides.
