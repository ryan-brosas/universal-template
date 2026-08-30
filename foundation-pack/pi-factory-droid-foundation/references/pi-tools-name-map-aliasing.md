<!-- capsule-v2 -->
# Cross-system tool-name alias maps — how do I map one logical tool across systems that rename, re-case, or prefix it?

**Source:** pi-factory-droid MIT `master@e0a53248ab173b6f0ff763441c1f1160bedd016e`; Codebase Memory `pi-factory-droid`. **Question:** When a host tool named `read file` becomes `read_file`, `pi-tools___read_file`, and `mcp_pi-tools_read_file` across the wire, how do I resolve any observed spelling back to the one original name?

## Register every alias up front; resolve with prefix-stripping fallback
**Path/Symbol:** `src/pi-tools-bridge.ts:registerNameMaps` (67-80), `resolvePiName` (82-90), `isOurTool` (92-94), `sanitizeToolName` (39-43), `mcpLlmId`/`mcpToolCatalogId` (21-27).
**Signature:** `registerNameMaps(tools: Tool[]): void; resolvePiName(droidToolName: string): string | undefined; sanitizeToolName(name: string): string` — `mcpLlmId(toolName) = \`${server}___${toolName}\``, `mcpToolCatalogId(toolName) = \`mcp_${server}_${toolName}\``.
**Data Shape:** Two public maps on the board: `llmNameToPi: Map<string,string>` (every accepted alias → original Pi tool name) and `piNameToSanitized: Map<string,string>`. Sanitization keeps `[a-zA-Z0-9_-]`, replaces the rest with `_`, and falls back to `"tool"` when empty.

### Decisive source
```ts
registerNameMaps(tools: Tool[]): void {
  this.llmNameToPi.clear();
  this.piNameToSanitized.clear();
  for (const t of tools) {
    const sanitized = sanitizeToolName(t.name);
    this.piNameToSanitized.set(t.name, sanitized);
    this.llmNameToPi.set(sanitized, t.name);
    this.llmNameToPi.set(sanitized.toLowerCase(), t.name);
    this.llmNameToPi.set(mcpLlmId(sanitized), t.name);
    this.llmNameToPi.set(mcpLlmId(sanitized).toLowerCase(), t.name);
    this.llmNameToPi.set(t.name, t.name);
    this.llmNameToPi.set(t.name.toLowerCase(), t.name);
  }
}

resolvePiName(droidToolName: string): string | undefined {
  return (
    this.llmNameToPi.get(droidToolName) ||
    this.llmNameToPi.get(droidToolName.toLowerCase()) ||
    // strip server prefix if present
    this.llmNameToPi.get(droidToolName.split("___").pop() || "") ||
    undefined
  );
}
```

**Flow:** at MCP-server build time (`buildPiToolsMcpServer` calls `board.registerNameMaps(tools)` first) every tool's plausible wire spellings are registered as aliases of the ORIGINAL name; at event time an incoming foreign name is looked up verbatim, lowercased, then server-prefix-stripped before being declared unknown. `isOurTool(name)` is just `resolvePiName(name) !== undefined` — the gate that decides whether a Droid tool call belongs to the bridge or stays native.
**Invariant:** The value stored is ALWAYS the original un-sanitized Pi tool name — resolution never returns a mangled form, so downstream host dispatch uses exactly the names it registered. Maps are cleared-and-rebuilt per registration so a rebuilt tool set never leaks stale aliases. Unknown names resolve to `undefined`, never throw.
**Probe:** `test/pi-tools-bridge.test.ts:101-104` pins `"pi-tools___bash"` as the llm id and `sanitizeToolName("read file") === "read_file"`; the board tests at :29-54 exercise resolution through the alias `"pi-tools___bash"` vs plain `"bash"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-factory-droid", query: "registerNameMaps resolvePiName sanitizeToolName mcpLlmId isOurTool", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt register-all-aliases-eagerly + lookup-with-fallbacks over ad-hoc string munging at each call site; adopt "resolve to the original name or undefined" as the ownership gate for hybrid agents. Adapt the alias set (your systems' casing/prefix conventions) and the separator. Omit the literal `___`/`mcp_` conventions unless you keep the matching catalog ids.
