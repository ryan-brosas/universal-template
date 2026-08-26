<!-- capsule-v2 -->
# Enterprise policy gate — how do allow/deny MCP server policies combine name, command, and URL entries without a config-shaped bypass?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What is the exact admission rule for allowedMcpServers/deniedMcpServers including the empty-allowlist and entry-kind-mismatch cases?

## Deny-first, empty-allowlist-blocks-all, kind-strict matching
**Path/Symbol:** `src/services/mcp/config.ts`: `isMcpServerDenied` (:364-408), `isMcpServerAllowedByPolicy` (:417-508), generic filter `filterMcpServersByPolicy<T>` (:536-551), allowlist source restriction `getMcpAllowlistSettings`/`shouldAllowManagedMcpServersOnly` (:341-346,:1485-1489), denylist always merged from ALL sources (:353-355).
**Signature:** entries are discriminated: `{serverName}` | `{serverCommand: string[]}` | `{serverUrl: pattern}`; matching helpers `commandArraysMatch` (exact array equality :149-154) and `urlMatchesPattern` (`*` wildcard → `.*`, everything else regex-escaped, full anchors :320-334).
**Data Shape:** `allowedMcpServers?: Entry[]`, `deniedMcpServers?: Entry[]`; SDK-type servers are EXEMPT from filtering (:520-524 — they're SDK-managed transport placeholders; URL/command entries are meaningless for them and name-gating would silently drop them in installPluginsAndApplyMcpInBackground carry-forward).

### Decisive source
```ts
// Denylist takes absolute precedence
if (isMcpServerDenied(serverName, config)) return false
if (!settings.allowedMcpServers) return true          // undefined = unrestricted
if (settings.allowedMcpServers.length === 0) return false   // EMPTY = block all
const hasCommandEntries = settings.allowedMcpServers.some(isMcpServerCommandEntry)
const hasUrlEntries     = settings.allowedMcpServers.some(isMcpServerUrlEntry)
if (config) {
  const serverCommand = getServerCommandArray(config)
  const serverUrl = getServerUrl(config)
  if (serverCommand) {            // stdio server
    if (hasCommandEntries) return matched(commandEntries) ? true : false
    // No command entries → name-based allowance only for stdio
    ...
  } else if (serverUrl) {         // remote server
    if (hasUrlEntries) return matched(urlEntries) ? true : false
    // No URL entries → name-based allowance only for remote
```

**Flow:** every user-controlled config ENTRY POINT that bypasses getClaudeCodeMcpConfigs must call `filterMcpServersByPolicy` — the two named callsites are `--mcp-config` (main.tsx) and `mcp_set_servers` control message (print.ts SDK V2) (:515-518). Denylist checks run even when allowManagedMcpServersOnly locks the ALLOWLIST to managed settings, because "users can always deny servers for themselves" (:349-352).
**Invariant:** An allowlist containing ONLY command entries blocks all remote servers even if their names appear as name entries (kind-strict); deny always wins over allow; the empty array is meaningful (block-all) and must not be conflated with undefined.
**Probe:** `grep -n 'settings.allowedMcpServers.length === 0' src/services/mcp/config.ts` (`432:`) and `grep -n "c.type === 'sdk' || isMcpServerAllowedByPolicy(name, c)" src/services/mcp/config.ts` (`544:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "filterMcpServersByPolicy", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "isMcpServerAllowedByPolicy", limit: 5 });
```

## Verdict
Adopt deny-first + empty-means-block-all + kind-strict entry matching + SDK exemption. Adapt settings-source plumbing. Omit plugin-only policy interactions beyond the documented callsites.
