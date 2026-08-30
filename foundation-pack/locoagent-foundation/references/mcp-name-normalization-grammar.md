<!-- capsule-v2 -->
# Tool-name grammar and normalization — how do `mcp__server__tool` names round-trip through parsing, permission checks, and the API's name charset?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How are MCP server/tool names normalized to the API pattern, how are tool names parsed back, and where does the known delimiter ambiguity live?

## charset sanitize + claude.ai underscore collapse + greedy-server parse asymmetry
**Path/Symbol:** `src/services/mcp/normalization.ts` (whole :1-23): `normalizeNameForMCP`, CLAUDEAI_SERVER_PREFIX `'claude.ai '`; `src/services/mcp/mcpStringUtils.ts`: `mcpInfoFromString` (:19-32), `buildMcpToolName` (:50-52), `getToolNameForPermissionCheck` (:60-67), documented ambiguity (:13-18).
**Signature:** normalize: `name.replace(/[^a-zA-Z0-9_-]/g, '_')`; claude.ai-prefixed names additionally `.replace(/_+/g,'_').replace(/^_|_$/g,'')`. Parse: `split('__')` with `[mcp, server, ...toolParts]`, tool rejoined via `join('__')`.
**Data Shape:** API pattern `^[a-zA-Z0-9_-]{1,64}$`; permission rules must target the fully-qualified name so a deny on builtin "Write" can't match an unprefixed MCP replacement.

### Decisive source
```ts
// mcpStringUtils.ts:13-18:
// Known limitation: If a server name contains "__", parsing will be incorrect.
// For example, "mcp__my__server__tool" would parse as server="my" and
// tool="server__tool" instead of server="my__server" and tool="tool". This is
// rare in practice since server names typically don't contain double underscores.
const parts = toolString.split('__')
const [mcpPart, serverName, ...toolNameParts] = parts
if (mcpPart !== 'mcp' || !serverName) return null
const toolName = toolNameParts.length > 0 ? toolNameParts.join('__') : undefined

// normalization.ts: claude.ai servers also collapse consecutive underscores and strip
// leading/trailing underscores to prevent interference with the __ delimiter used in
// MCP tool names.
```

**Flow:** server "My Server!" + tool "get-diff" → buildMcpToolName → `mcp__My_Server___get_diff`; permission checking uses getToolNameForPermissionCheck which rebuilds from mcpInfo (not display name); prompts additionally exist as `<server>:<skill>` for MCP skills — membership filters must accept BOTH shapes (`commandBelongsToServer`, utils.ts :52-62).
**Invariant:** The parser is deliberately greedy-for-tool (rejoins `__` in the TOOL part) but cannot recover multi-`__` SERVER names — validation should prevent `__` in server names upstream rather than fixing the parser; normalization differs by prefix so the same display name can normalize differently per source.
**Probe:** `grep -c "replace(/_+/g, '_')" src/services/mcp/normalization.ts` (`1`) and `grep -n 'toolNameParts.join' src/services/mcp/mcpStringUtils.ts` (`30:`) and `grep -n 'return tool.mcpInfo' src/services/mcp/mcpStringUtils.ts | head -1` (`64:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "mcpInfoFromString", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "normalizeNameForMCP", limit: 5 });
```

## Verdict
Adopt both files verbatim (~130 lines, dependency-free). Adapt the API charset constant. Document the server-name `__` limitation in your validator.
