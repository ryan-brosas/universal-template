<!-- capsule-v2 -->
# Fail-fast native args validation — what happens when the model's tool arguments don't match the schema?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How do you convert a complete native tool call into typed args while surviving every real-model quirk (unknown tools, unknown params, double-stringified arrays, hyphen/underscore drift, legacy formats), and where exactly do you fail fast vs coerce?

## Alias-resolve → validate name → per-tool minimum-args switch → throw if unconstructable
**Path/Symbol:** `src/core/assistant-message/NativeToolCallParser.ts` (`parseToolCall` :671-1034; `parseDynamicMcpTool` :1041-1076; coercion helpers `coerceOptionalNumber` :314-325 / `coerceOptionalBoolean` :76-90; file-entry conversion `convertFileEntries` :337-366).
**Signature:** `parseToolCall<TName extends ToolName>(toolCall: {id: string; name: TName; arguments: string}): ToolUse<TName> | McpToolUse | null`.
**Data Shape:** Result carries BOTH planes: `params: Partial<Record<ToolParamName, string>>` (stringified, display/logging only) and typed `nativeArgs` (**the ONLY plane execution may consume**); optional `originalName` (alias was used) and `usedLegacyFormat: true`.

### Decisive source
```ts
const normalizedName = normalizeMcpToolName(toolCall.name)   // mcp__srv__tool → mcp--srv--tool
if (normalizedName.startsWith(mcpPrefix)) return this.parseDynamicMcpTool({...toolCall, name: normalizedName})
const resolvedName = resolveToolAlias(toolCall.name as string) as TName   // edit_file → apply_diff etc.
if (!toolNames.includes(resolvedName) && !customToolRegistry.has(resolvedName)) return null  // invalid name

// Unknown PARAMS are warned-and-dropped, not fatal:
for (const [key, value] of Object.entries(args)) {
    if (!toolParamNames.includes(key) && !customToolRegistry.has(resolvedName)) { console.warn(...); continue }
    params[key] = typeof value === "string" ? value : JSON.stringify(value)
}
// ...per-tool switch validates MINIMUM required args and builds nativeArgs...
if (!nativeArgs && !customToolRegistry.has(resolvedName)) {
    throw new Error(`[NativeToolCallParser] Invalid arguments for tool '${resolvedName}'. ...`)
}   // caught by outer try → console.error + return null
```
Quirk handling inside the switch: read_file accepts legacy `{files:[...]}` FIRST (`usedLegacyFormat=true`, `_legacyFormat` marker), tolerating **double-stringified** arrays (`JSON.parse(string)` when `files` is a string); line ranges accepted as tuples `[1,50]`, objects `{start,end}`, or strings `"1-50"`; optional numbers/booleans coerced from numeric/`"true"`-style strings else `undefined`. Empty `arguments === ""` parses to `{}`. MCP names keep their ORIGINAL name in history while splitting server/tool via `--` separators.

**Flow:** normalize MCP-style names → route dynamic MCP to its own parser (typed `McpToolUse`, original name preserved) → alias-resolve + validate core/custom tool name → parse JSON (empty = {}) → build display params with warn-drop on unknown keys → per-tool switch constructs typed nativeArgs or throws → outer catch logs and returns `null`.
**Invariant:** Execution NEVER falls back to stringly `params`; an unconstructable payload is a hard failure surfaced as one structured error (not a silent empty call); alias resolution happens BEFORE validation so renamed tools stay valid; unknown parameters degrade to warnings because models invent extra fields constantly.
**Probe:** `src/core/assistant-message/__tests__/NativeToolCallParser.spec.ts:10-294` — minimal/slice/indentation read_file parsing, legacy files array (:102-269 incl. :241 double-stringified "model quirk"), :272 negative "should NOT set usedLegacyFormat for new format".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "parseToolCall nativeArgs resolveToolAlias invalid arguments", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-plane result (display params + execution-only nativeArgs), alias-before-validate ordering, warn-not-fail unknown params, and fail-fast-on-unconstructable. Adapt the per-tool arg schemas. Omit nothing: dropping any quirk branch re-breaks a documented live-model failure mode.
