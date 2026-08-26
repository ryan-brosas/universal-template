<!-- capsule-v2 -->
# Native-tool suppression allowlist — how do I stop a hybrid agent from using its native tools when a bridge owns the tool surface?

**Source:** pi-factory-droid MIT `master@e0a53248ab173b6f0ff763441c1f1160bedd016e`; Codebase Memory `pi-factory-droid`. **Question:** After injecting my own tools into a foreign agent, how do I disable its built-in tools without guessing their ids?

## Compute the disable list FROM the live catalog, keeping bridge ids plus an escape-hatch tool
**Path/Symbol:** `src/pi-tools-bridge.ts:selectDisableToolIds` (216-235); applied at `src/providers.ts:718-730`.
**Signature:** `selectDisableToolIds(catalog: Array<{ id: string; llmId?: string }>, tools: Tool[]): string[]`
**Data Shape:** `catalog` = the live agent's own tool listing (`created.listTools()` → `{tools}`); `tools` = the host tools already bridged as MCP. Returns catalog ids to write into `updateSettings({ disabledToolIds })`.

### Decisive source
```ts
export function selectDisableToolIds(catalog, tools): string[] {
  const keep = new Set<string>();
  keep.add("tool-search-cli");                       // escape hatch stays enabled
  for (const t of tools) {
    const sanitized = sanitizeToolName(t.name);
    keep.add(mcpToolCatalogId(sanitized));           // mcp_pi-tools_<name>
    keep.add(mcpLlmId(sanitized));                   // pi-tools___<name>
  }
  return catalog
    .map((t) => t.id)
    .filter((id) => {
      if (!id) return false;
      if (keep.has(id)) return false;
      if (id.startsWith(`mcp_${PI_TOOLS_MCP_SERVER}_`)) return false;
      return true;                                   // everything else: disable
    });
}
```

Application with compensating cleanup on failure:
```ts
if (opts.mode === "pi-tools") {
  try {
    const listed = await created.listTools();
    const disableIds = selectDisableToolIds(listed.tools ?? [], tools);
    if (disableIds.length) {
      await created.updateSettings({ disabledToolIds: disableIds });
    }
  } catch (error) {
    await created.close().catch(() => {});
    await mcpServer?.close().catch(() => {});
    throw error;
  }
}
```

**Flow:** session created WITH the MCP server attached → `listTools()` reads the agent's real tool catalog → allowlist = tool-search + every bridged tool's two id forms + any `mcp_pi-tools_*` id → the complement inside the catalog becomes `disabledToolIds` → a mid-creation failure closes BOTH the session and the MCP server before rethrowing, so no half-configured entry enters the pool.
**Invariant:** The disable list is derived from the LIVE catalog, never hardcoded — new native tools are suppressed automatically and unknown bridge-id spellings can never be disabled by accident (both id forms plus the prefix guard are kept). Suppression is best-effort configuration, not security: `handleDroidEvent` still re-checks `board.isOurTool(name)` at event time.
**Probe:** `test/pi-tools-bridge.test.ts:56-72` ("keeps tool-search and pi-tools MCP ids"): disables `execute-cli` and `mcp_linear_get_issue`, keeps `tool-search-cli` and `mcp_pi-tools_bash`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-factory-droid", query: "selectDisableToolIds listTools disabledToolIds updateSettings", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt complement-of-allowlist over enumerate-and-disable: derive what to turn off from what the runtime actually reports, keep one discovery/escape tool, and treat event-time ownership checks as the real gate. Adapt the keep-set to your agent's discovery tool and id conventions. Omit the Droid settings API shape.
