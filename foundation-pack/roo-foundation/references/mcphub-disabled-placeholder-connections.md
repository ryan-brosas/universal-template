<!-- capsule-v2 -->
# Placeholder connections for disabled servers — how do you keep a globally-disabled or per-server-disabled server visible in the UI without ever opening a transport?

**Source:** Roo-Code (Roo Code, Inc.) Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** When MCP is disabled (globally or per server), how does the hub still track the server so the settings UI can show and re-enable it?

## DisconnectedMcpConnection placeholder + two-reason enum
**Path/Symbol:** `src/services/mcp/McpHub.ts` (`createPlaceholderConnection` :620–640; `DisableReason` enum :61–64; consumers `connectToServer` :667–682; `refreshAllConnections` disabled branch :1302–1316).
**Signature:** `private createPlaceholderConnection(name: string, config: z.infer<typeof ServerConfigSchema>, source: "global" | "project", reason: DisableReason): DisconnectedMcpConnection`.
**Data Shape:** returns `{ type: "disconnected", server: { name, config: JSON.stringify(config), status: "disconnected", disabled: reason === SERVER_DISABLED ? true : config.disabled, source, projectPath?, errorHistory: [] }, client: null, transport: null }`.

### Decisive source
```ts
// :61-64 — WHY the placeholder exists is carried in the reason, not inferred later
export enum DisableReason {
    MCP_DISABLED = "mcpDisabled",
    SERVER_DISABLED = "serverDisabled",
}
```
```ts
// :632 — the ONLY place the two reasons behave differently
disabled: reason === DisableReason.SERVER_DISABLED ? true : config.disabled,
```
```ts
// :669-674 (global gate) / :677-682 (per-server gate) — both push placeholders instead of returning bare
const mcpEnabled = await this.isMcpEnabled()
if (!mcpEnabled) {
    const connection = this.createPlaceholderConnection(name, config, source, DisableReason.MCP_DISABLED)
    this.connections.push(connection)
    return
}
```

**Flow:** `connectToServer` checks global enable → per-server `config.disabled` → either way a null-client placeholder enters `connections`, so listings/UI keep the entry; `restartConnection` early-returns when globally disabled (:1258–1262) leaving existing entries untouched; re-enabling flows through normal `updateServerConnections`, where deepEqual sees unchanged configs and only missing connections get built.
**Invariant:** disabled servers must remain IN `connections` (never filtered out at ingest) because `getServers()` filters `!conn.server.disabled` at READ time (:455) — filtering earlier would destroy the config needed to reconnect; `callTool`/`readResource` still throw `"Server \"X\" is disabled"` on the placeholder (:1716–1718/:1742–1744), so visibility never implies usability.
**Probe:** `src/services/mcp/__tests__/McpHub.spec.ts`: it `"should use MCP_DISABLED reason when MCP is globally disabled"` (:516–543) vs it `"should use SERVER_DISABLED reason when server is individually disabled"` (:544–567); plus describe `"Discriminated union type handling"` it `"should create disconnected connections for disabled servers"` (:249–281).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "DisableReason mcpDisabled serverDisabled placeholder connection", limit: 5 });
// Method row McpHub.connectToServer 655-896 carries both gates; class cluster query family resolves line-exact (total ≥7)
```

## Verdict
Adopt placeholder-with-reason over silent omission — the enum is what makes re-enable correct. Adapt the enable-state source (VSCode global state here). Omit nothing.
