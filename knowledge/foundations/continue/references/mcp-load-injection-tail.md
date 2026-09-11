<!-- capsule-v2 -->
# MCP load-injection tail — what does a connected server contribute at config-load time, and how do its tools stay addressable?

**Source:** continue Apache-2.0 `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does a porter fold external tool servers into a compiled config — naming, identity URIs, prompt prefetch, and failure posture — without making the load fatal?

## Four contributions per connected server + normalized names + mcp:// identity
**Path/Symbol:** `core/config/profile/doLoadConfig.ts:194–289` (injection tail); `core/tools/mcpToolName.ts` (whole, 18 lines); `core/tools/callTool.ts:52–65` (`encodeMCPToolUri`/`decodeMCPToolUri`) and `:67–113` (`callToolFromUri` mcp branch).
**Signature:** `getMCPToolName(server: MCPServerStatus, tool: MCPTool): string`; `encodeMCPToolUri(mcpId: string, toolName: string): string`; `decodeMCPToolUri(uri: string): [string, string] | null`.
**Data Shape:** injected tool = `{ displayTitle: "<server> <tool>", function: { name: <prefixed>, description, parameters: inputSchema }, uri: "mcp://<enc id>/<enc name>", group, originalFunctionName, mcpMeta, readonly: false, type: "function" }`.

### Decisive source
```ts
const serverPrefix = serverName.toLowerCase()
  .replace(/[^a-z0-9]+/g, "_")
  .replace(/^_+|_+$/g, "")   // trim edge underscores
  .replace(/_+/g, "_");      // collapse runs
if (toolName.startsWith(serverPrefix)) return toolName; // idempotent skip
return `${serverPrefix}_${toolName}`;

// identity: encode/decode round-trip through a dedicated protocol
return `mcp://${encodeURIComponent(mcpId)}/${encodeURIComponent(toolName)}`;
```

**Flow:** each CONNECTED server contributes FOUR things at load time: (1) tools mapped to prefixed names with `mcp://` URIs; (2) slash commands whose prompt content is PREFETCHED during load via `mcpManager.getPrompt` — fail-soft to `promptContent: undefined` so the UI shows a fallback; (3) an `MCPContextProvider` submenu of resources + resourceTemplates (only when non-empty); (4) statuses with the live client destructured OUT (`{ client, ...rest }`) so only serializable state enters config; server errors surface as NON-fatal config errors. After injection, built-ins are appended (`getConfigDependentToolDefinitions`, see tool-definition-gating-matrix.md), then duplicate-name detection warns non-fatally. At CALL time `callToolFromUri` routes http(s) vs `mcp:`, decodes host=mcpId / pathname-slice-1=toolName, coerces args to the tool's schema, and throws on `isError === true`.
**Invariant:** nothing an MCP server does can fatally break config load — connection errors become error entries; prompt prefetch failures become undefined content. Name normalization is deterministic so model-facing tool names stay `[a-z0-9_]`; the prefix skip makes re-loading idempotent.
**Probe:** `core/tools/mcpToolName.vitest.ts` (9 cases pin the ladder end-to-end, e.g. `"Linear MCP (SSE)"` + `create_issue` ⇒ `linear_mcp_sse_create_issue`; `"Linear__MCP"` ⇒ no double underscore; already-prefixed name passes through unchanged).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "mcp tool name normalize encode uri decode call", limit: 10 });
```

## Verdict
Adopt the four-contribution shape per connected server, prefetch-with-fallback for remote prompts, client-stripped serializable statuses, the normalization ladder with idempotent prefix skip, and the scheme-tagged URI identity that decodes without registry lookup; adapt the prefix character set to your model's tool-name constraints; omit the MCP UI-resource fetch branch unless your client renders server UI. Trap: `decodeURIComponent(url.hostname)` means server ids containing characters encodeURIComponent escapes into the host position must not contain `/` or `:` — keep ids hostname-safe.
