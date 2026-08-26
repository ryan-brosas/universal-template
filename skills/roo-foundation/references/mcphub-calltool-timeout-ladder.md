<!-- capsule-v2 -->
# callTool timeout resolution ladder — how do you derive a per-call tool timeout from a stored JSON config string when that parse can fail at any point?

**Source:** Roo-Code (Roo Code, Inc.) Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How is the tools/call request timeout computed, and what happens when the server's stored config fails to re-parse?

## Re-parse stored config per call; fall back to 60s on ANY failure
**Path/Symbol:** `src/services/mcp/McpHub.ts` (`callTool` :1730–1769, timeout block :1746–1754; schema default :69).
**Signature:** `async callTool(serverName: string, toolName: string, toolArguments?: Record<string, unknown>, source?: "global" | "project"): Promise<McpToolCallResponse>`.
**Data Shape:** `connection.server.config` is a JSON STRING (snapshot taken at connect time); timeout unit conversion ×1000 at the boundary (schema seconds → SDK ms).

### Decisive source
```ts
// :1746-1754
let timeout: number
try {
    const parsedConfig = ServerConfigSchema.parse(JSON.parse(connection.server.config))
    timeout = (parsedConfig.timeout ?? 60) * 1000
} catch (error) {
    console.error("Failed to parse server config for timeout:", error)
    // Default to 60 seconds if parsing fails
    timeout = 60 * 1000
}
```
```ts
// :69 — schema-level default (parse-time), distinct from the runtime fallback above
timeout: z.number().min(1).max(3600).optional().default(60),
```

**Flow:** find connection (typed-narrowed to `connected`, else loud error telling the model to use 'Connected MCP Servers' :1737–1741) → disabled check throws → parse stored config string through the FULL schema again → `?? 60` catches absent-after-parse, catch-block catches unparseable JSON/schema rejection → pass `{ timeout }` as the third argument of `client.request` (:1756–1768).
**Invariant:** there are TWO independent default-60 mechanisms — schema `.default(60)` for validated configs and the `?? 60` + catch fallback for corrupt ones; both must survive a port or a corrupt config turns into an infinite-hang tool call. Bounds (`min(1).max(3600)`) are enforced by the schema re-parse here, not trusted from connect time.
**Probe:** `src/services/mcp/__tests__/McpHub.spec.ts`: it `"should use default timeout of 60 seconds if not specified"` (:1489–1511 asserts `objectContaining({ timeout: 60000 })` on the mocked request), it `"should apply configured timeout to tool calls"` (:1513–1535 asserts 120000), it `"should fallback to default timeout when config has invalid timeout"` (:1585–1655).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "callTool timeout configuration default 60 seconds", limit: 5 });
// Method row McpHub.callTool src/services/mcp/McpHub.ts 1730-1769 resolves in the validateServerConfig query family (total: 7)
```

## Verdict
Adopt per-call re-parse with the double default. Adapt bounds to your host's longest legitimate tool. Omit the user-facing error copy.
