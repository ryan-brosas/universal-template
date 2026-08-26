<!-- capsule-v2 -->
# MCP result → pi — schema→TypeBox, result mapping, sanitization, projectPath injection

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How does the pi extension convert a remote MCP tool's JSON Schema into a pi `registerTool` TypeBox schema, map an MCP result into pi text/image content, and sanitize secrets?

## MCP result → pi
**Path/Symbol:** `src/pi-extension/acp-mcp-bridge.ts` — `schemaToTypeBox` (105-202), `objectSchema` (204-236), `mcpResultToPiResult` (347-405), `prepareToolArguments` (277-287), `sanitize` (242-256), `registerTools` (424-491).
**Signature:** `schemaToTypeBox(schema: JsonSchema, state?): TSchema`; `mcpResultToPiResult(value: unknown): PiMcpToolResult`; `prepareToolArguments(tool, args, projectPath?): Record<string, unknown>`.
**Data Shape:** Conversion guards: `MAX_SCHEMA_DEPTH=32`, `MAX_SCHEMA_NODES=2000`, `MAX_RESULT_DEPTH=8`, `MAX_RESULT_ITEMS=100`, `MAX_RESULT_STRING=40_000`, `MAX_IMAGE_BYTES=8MiB`. Result content blocks: text/image/resource/resource_link.

### Decisive source
```ts
// schemaToTypeBox: JSON Schema -> TypeBox with depth/node guards, $ref/cycle handling
if (state.depth > MAX_SCHEMA_DEPTH || state.nodes > MAX_SCHEMA_NODES) { state.warnings.push('schema widened'); return Type.Any() }
const reference = schema.$ref
if (typeof reference === 'string') {
  const target = state.references.get(reference)
  if (!target) { state.warnings.push(`unresolved JSON Schema reference widened: ${reference}`); return Type.Any() }
  if (state.resolving.has(reference)) { state.warnings.push(`cyclic JSON Schema reference widened: ${reference}`); return Type.Any() }
  // ... recurse with resolving set
}
// anyOf/oneOf -> union, allOf -> intersect; nullable -> union with Type.Null()
// string/number/integer/boolean/null/array(tuple via prefixItems)/object/any
```
```ts
// mcpResultToPiResult: map MCP result -> pi text/image content
if (result.isError === true) throw new McpToolError(`MCP tool reported an error\n${stringify(safeResult)}`, { code:'mcp_is_error', result: safeResult })
for (const block of result.content ?? []) {
  if (block.type === 'text' && typeof block.text === 'string') content.push({ type:'text', text: block.text })
  else if (block.type === 'image' && typeof block.data === 'string' && typeof block.mimeType === 'string' && Buffer.byteLength(block.data,'base64') <= MAX_IMAGE_BYTES)
    content.push({ type:'image', data: block.data, mimeType: block.mimeType })
  else if (block.type === 'resource' && block.resource) content.push({ type:'text', text: `[resource ${uri}]\n${resource.text}` })
  else if (block.type === 'resource_link' && typeof block.uri === 'string') content.push({ type:'text', text: `[resource link ${block.uri}]` })
  else unsupported.push(sanitize(block))
}
if (content.length === 0 && result.structuredContent !== undefined) content.push({ type:'text', text: stringify(sanitize(result.structuredContent)) })
if (content.length === 0) content.push({ type:'text', text: 'MCP tool returned no textual content.' })
```
```ts
// sanitize: redact sensitive keys, bound depth/items/string length
if (isSensitiveKey(key)) output[key] = REDACTED   // /token|secret|password|authorization|cookie|api[-_]?key|private[-_]?key/i
```
```ts
// prepareToolArguments: inject projectPath only if the schema declares it and it's not already set
if (projectPath && prepared.projectPath === undefined && hasSchemaProperty(tool.inputSchema, 'projectPath')) prepared.projectPath = projectPath
```

**Flow:** `registerTools` converts each remote tool's `inputSchema` to a TypeBox schema via `schemaToTypeBox` (with warnings for widened constructs), registers it with `pi.registerTool`, and records success/failure + schema hash. On execution, `prepareToolArguments` injects `projectPath` when the schema declares it; the call is forwarded over IPC; the result comes back and `mcpResultToPiResult` maps it to pi text/image content (rejecting `isError`, redacting sensitive keys, bounding size). A `McpToolError` is thrown for malformed/error results rather than hiding them as successful text.

**Invariant:** Schema conversion never throws on exotic JSON Schema — it widens to `Type.Any()` with a warning (never crashes registration); MCP `isError` results surface as tool errors, not successful text; sensitive keys are redacted in surfaced details; image blocks over 8MiB are dropped to unsupported.

**Probe:** `test/unit/acp-mcp-extension.test.ts` ("ACP MCP Pi extension conversion" describe block) — pins schema→TypeBox and result mapping.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "schemaToTypeBox mcpResultToPiResult prepareToolArguments", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the guarded JSON Schema→TypeBox conversion, the MCP-result→pi-content mapping with `isError` rejection, secret redaction, and `projectPath` injection. Adapt the pi `registerTool` signature and the `PiMcpToolResult` shape to the target agent. Omit the IntelliJ-specific `toolDescription` guidance notes and the `McpToolError` details unless the target surfaces structured errors.
