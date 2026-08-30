<!-- capsule-v2 -->
# Sanitized-name registry + fuzzy fallback — how do you map a model-mangled MCP server name (hyphens→underscores) back to the real connection without collisions?

**Source:** Roo-Code (Roo Code, Inc.) Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** When tool calls arrive with sanitized or model-corrupted server names, how does the hub resolve them back to actual connections in bounded, deterministic steps?

## Exact → registry → fuzzy ladder
**Path/Symbol:** `src/services/mcp/McpHub.ts` (`sanitizedNameRegistry` field :163; register on connect :663–665; delete-on-last :1101–1106; resolver `findServerNameBySanitizedName` :958–978). Grammar: `src/utils/mcp-name.ts` (`sanitizeMcpName` :90–115, `normalizeForComparison` :27–29, `toolNamesMatch` :188–190, separator/prefix consts :13–18).
**Signature:** `public findServerNameBySanitizedName(sanitizedServerName: string): string | null`.
**Data Shape:** registry = `Map<sanitizedName, originalName>`, maintained at connect/disconnect so it never outlives its connection set.

### Decisive source
```ts
// :959-977 — three-rung resolution, cheapest first
const exactMatch = this.connections.find((conn) => conn.server.name === sanitizedServerName)
if (exactMatch) { return exactMatch.server.name }
const registryMatch = this.sanitizedNameRegistry.get(sanitizedServerName)
if (registryMatch) { return registryMatch }
// Use fuzzy matching: treat hyphens and underscores as equivalent
const fuzzyMatch = this.connections.find((conn) => toolNamesMatch(conn.server.name, sanitizedServerName))
if (fuzzyMatch) { return fuzzyMatch.server.name }
return null
```
```ts
// mcp-name.ts :101-107 — sanitization kills the "--" separator ambiguity AT THE SOURCE
sanitized = sanitized.replace(/[^a-zA-Z0-9_\-]/g, "")
sanitized = sanitized.replace(/--+/g, "-")     // no sanitized name can contain the separator
if (!/^[a-zA-Z_]/.test(sanitized)) { sanitized = "_" + sanitized }
```

**Flow:** connect registers `registry[sanitizeMcpName(name)] = name`; disconnect deletes the key only when NO connections with that name remain (:1102–1106 — same-name global+project pairs share one registry entry). Resolution tries exact, then registry, then `-`/`_`-equivalence over live connections.
**Invariant:** sanitizeMcpName collapses `--+→-`, guaranteeing a sanitized name can never CONTAIN the wire separator `--` (`MCP_TOOL_SEPARATOR`), which is what makes `parseMcpToolName`'s split well-defined; the registry must be deleted exactly when the last same-name connection dies, else a stale entry resurrects a dead server's identity.
**Probe:** direct unit spec for the grammar: `src/utils/__tests__/mcp-name.spec.ts` (pins sanitize/normalize/parse round-trips); hub-side behavior exercised via describe `"server disabled state"` it `"should prevent calling tools on disabled servers"` (:1360–1390) where callTool resolves through findConnection.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "sanitizeMcpName buildMcpToolName separator", limit: 5 });
// CLI verified @ pin: rank#1 line-exact → Function src/utils/mcp-name.ts sanitizeMcpName 90-115 (total: 5)
```

## Verdict
Adopt the three-rung ladder and the `--+→-` collapse invariant. Adapt the 64-char cap context if your API allows longer function names. Omit nothing — dropping any rung converts a typo-tolerant UX into hard failures.
