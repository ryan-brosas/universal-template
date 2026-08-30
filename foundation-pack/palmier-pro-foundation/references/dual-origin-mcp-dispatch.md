<!-- capsule-v2 -->
# Dual-origin MCP dispatch — how does one executor serve both the in-app chat and external MCP clients?

**Source:** PalmierPro GPL-3.0 `main@49841f35b3eafa65c7eadc7b168bcc74db632906`; Codebase Memory `palmier-pro`. **Question:** How do you expose a subset of in-app agent tools over MCP without duplicating handlers or letting external clients touch everything?

## MCPService.registerTools / dispatchCall + session pinning
**Path/Symbol:** `Sources/PalmierPro/Agent/MCP/MCPService.swift:registerTools` (79–91), `dispatchCall` (94–98); `ToolDefinitions.ToolArgsBridge.argsFromMCP` (`Sources/PalmierPro/Agent/Tools/ToolDefinitions.swift:1413–1418`); gating in `ToolExecutor.executeWithOrigin` (92–97).
**Signature:** `nonisolated static func registerTools(on server: Server, executor: ToolExecutor) async`; `private static func dispatchCall(_ params: CallTool.Parameters, executor: ToolExecutor) async -> CallTool.Result`.
**Data Shape:** MCP surface = `ToolDefinitions.mcpServer` subset of `ToolDefinitions.inAppAgent`; args converted from MCP `Value` to `[String: Any]`; result converted via `ToolResult.toMCPResult()`.

### Decisive source
```swift
await server.withMethodHandler(ListTools.self) { _ in .init(tools) }
await server.withMethodHandler(CallTool.self) { params in
    await dispatchCall(params, executor: executor)
}
// dispatchCall:
let args = ToolArgsBridge.argsFromMCP(params.arguments ?? [:])
let result = await executor.execute(name: params.name, args: args, source: "mcp")
return result.toMCPResult()
```
Origin gate inside the shared envelope:
```swift
guard let tool = ToolName(rawValue: name),
      origin.source != "mcp" || ToolDefinitions.mcpServer.contains(where: { $0.name == tool })
else { ... return ToolResult.error("Unknown tool: \(name)") }
```

**Flow:** app boot registers ListTools/CallTool once per server → external client calls → args bridged → same `execute` path as the in-app agent but with `source: "mcp"` → allow-list enforced inside the envelope → per-MCP-session executors are created from a project provider (`makeSessionToolExecutor`) so an external session stays pinned to the project visible at session start while in-app chat keeps following local selection.
**Invariant:** MCP callers can never reach tools outside `mcpServer` even by guessing names; a pinned MCP session's reads and writes target its captured project; unknown/unrecognized MCP tool names do NOT activate a session.
**Probe:** `Tests/PalmierProTests/Agent/ManageProjectToolTests.swift:59-80` (`mcpSessionPinsProjectWhileInAppChatStaysLocal`: provider switch mid-session doesn't move the session; `create_timeline` blocked for pinned read-only view but fine in-app), `:82-92` (`mcpSessionActivatesOnFirstRecognizedToolCall`: `not_a_palmier_tool` with source "mcp" leaves `mcpSessionActivation.isActivated == false`, then `get_timeline` with "mcp" activates it), `:9-27` (`replacesIndividualProjectTools`: mcpServer contains `manage_project`, not the four individual project tools).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "palmier-pro", query: "MCPService registerTools dispatchCall makeSessionToolExecutor", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt: one executor, two origins, subset allow-list enforced *inside* the executor (not only at registration), per-session project pinning via a provider closure, activation only on recognized calls. Adapt the transport (swift-sdk Server here; PalmierPro also ships a standalone `mcpb/server/index.js` bridge — separate pass). Omit Convex-backed model catalog exposure. Coverage: MCPService.swift + ToolDefinitions.swift `no_recorded_issue` @ gen 2026-08-25T19:59:55Z; ManageProjectToolTests read directly.
