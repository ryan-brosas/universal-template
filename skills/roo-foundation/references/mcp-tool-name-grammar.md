<!-- capsule-v2 -->
# MCP tool-name grammar — how do dynamic server tools survive provider function-name rules and model separator drift?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How do you encode `server/tool` pairs into API-safe function names, and parse them back when models rewrite the separators?

## `mcp--server--tool` wire format with fuzzy underscore round-trip
**Path/Symbol:** `src/utils/mcp-name.ts` (`MCP_TOOL_PREFIX` :18 / `MCP_TOOL_SEPARATOR` :13, `normalizeForComparison` :27-30, `normalizeMcpToolName` :44-64, `isMcpTool` :74-76, `sanitizeMcpName` :90-115).
**Signature:** `normalizeMcpToolName(toolName: string): string`; `parseMcpToolName(name: string): {serverName, toolName} | undefined`; `sanitizeMcpName(name: string): string`.
**Data Shape:** Wire name = `mcp--<sanitizedServer>--<sanitizedTool...>` (`--` chosen because it survives every provider's function-name charset and cannot collide with underscores inside sanitized names).

### Decisive source
```ts
// Models (especially Claude) emit mcp__srv__tool for mcp--srv--tool:
const normalized = normalizeForComparison(toolName)        // '-' → '_' for DETECTION only
if (normalized.startsWith("mcp__")) {
    const parts = toolName.split(/__|--/)                   // split on BOTH separators
    if (parts.length >= 3 && parts[0].toLowerCase() === "mcp") {
        const toolNamePart = parts.slice(2).join("--")      // rejoin: tool itself may contain '_'
        return `mcp--${parts[1]}--${toolNamePart}`
    }
}
```
Sanitization for the OUTBOUND direction: spaces→underscores, strip everything outside `[A-Za-z0-9_-]`, collapse any `--+` run to a single `-` (**so a sanitized name can never contain the `--` separator it will later be split on**), prefix `_` if it doesn't start with a letter/underscore, fallback `_` when empty.

**Flow:** register tool → sanitize server+tool names → join as `mcp--server--tool` → provider/model may mutate separators → inbound parse first normalizes hyphens-to-underscores purely for detection, splits on both dialects, rejoins the tail so only the FIRST two separators are structural.
**Invariant:** Detection is fuzzy but reconstruction is canonical — the parsed-back name always uses `--`; sanitized components are guaranteed separator-free; a tool whose own name contains underscores still round-trips because splitting is anchored at `mcp{sep}server{sep}`.
**Probe:** `src/utils/__tests__/mcp-name.spec.ts` (dedicated suite pinning normalize/sanitize round-trips incl. underscore-drift cases); parser-side integration in NativeToolCallParser.spec.ts MCP paths.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "mcp name sanitize normalize separator", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the double-hyphen grammar + detect-fuzzy/rejoin-tail parsing + separator-collapsing sanitization as one unit — each piece exists to make the others safe. Adapt the prefix constant. Omit nothing: removing the `--+→-` collapse or the tail-rejoin breaks round-tripping for real server names.
