<!-- capsule-v2 -->
# Config scope merge and signature dedup — how do six config sources merge without duplicate servers launching the same connection twice?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** In what precedence do enterprise/user/project/local/dynamic/plugin/claude.ai MCP configs merge, and how are content-duplicates suppressed when keys never collide?

## Precedence merge + stdio:/url: signatures + CCR proxy unwrapping
**Path/Symbol:** `src/services/mcp/config.ts`: merge in getClaudeCodeMcpConfigs (:1071-1251; final `Object.assign({}, dedupedPluginServers, userServers, approvedProjectServers, localServers)` :1231-1238); `dedupPluginMcpServers` (:223-266) + `dedupClaudeAiMcpServers` (:281-310); `getMcpServerSignature` (:202-212) + `unwrapCcrProxyUrl` (:171-193); project-scope parent traversal (:909-961, closest-to-cwd wins via reverse iteration); getAllMcpConfigs claude.ai overlap (:1258-1290).
**Signature:** `getMcpServerSignature(config): string | null` → `` `stdio:${jsonStringify([command, ...args])}` `` or `` `url:${unwrapCcrProxyUrl(url)}` `` or null (sdk).
**Data Shape:** Signature deliberately IGNORES env (plugins always inject CLAUDE_PLUGIN_ROOT) and headers ("same URL = same server regardless of auth"). Suppression record `{name, duplicateOf}` surfaces in UI as informational errors (`mcp-server-suppressed-duplicate` :1218-1229).

### Decisive source
```ts
// Manual wins over plugin; between plugins, first-loaded wins. (:223)
// Only enabled manual servers count as dedup targets — a disabled manual server
// mustn't suppress its connector twin, or neither runs. (:276-280)
for (const [name, config] of Object.entries(manualServers)) {
  if (isMcpServerDisabled(name)) continue          // disabled manual ≠ dedup target
  const sig = getMcpServerSignature(config)
  if (sig && !manualSigs.has(sig)) manualSigs.set(sig, name)
}
// CCR proxy URLs preserve the original vendor URL in mcp_url query param so
// signature-based dedup matches plugin raw URL against connector proxy URL (:165-170)
```

**Flow:** enterprise config exists ⇒ EXCLUSIVE (return filtered enterprise-only, :1082-1096). Otherwise: load scopes (project = every .mcp.json from root to cwd, closer overrides) → filter project servers to `approved` status → build enabled-manual set (enabled ∧ policy-allowed) → split plugin servers enabled/disabled so a DISABLED plugin can't win first-plugin-wins against an enabled twin (:1195-1210) → dedup plugins vs enabled-manual then plugin-vs-plugin → merge with precedence plugin < user < project < local → final policy filter. getAllMcpConfigs additionally starts the memoized claude.ai fetch BEFORE awaiting getClaudeCodeMcpConfigs so it overlaps plugin loading (:1267-1276), then suppresses connectors whose normalized URL equals an enabled manual server.
**Invariant:** Dedup targets must be ENABLED servers only (else both twins go dead); signatures compare CONNECTION IDENTITY (command array / unwrapped URL), never names or auth headers.
**Probe:** `grep -nF 'stdio:${jsonStringify(cmd)}' src/services/mcp/config.ts` (`205:`) and `grep -n \"parsed.searchParams.get('mcp_url')\" src/services/mcp/config.ts` (`188:`) and `grep -n \"isMcpServerDisabled(name)) continue\" src/services/mcp/config.ts` (`290:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "dedupPluginMcpServers", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "unwrapCcrProxyUrl", limit: 5 });
```

## Verdict
Adopt signature-based content dedup with enabled-only targets and proxy-URL unwrapping. Adapt scope set and precedence order to your product. Omit claude.ai connector fetching specifics beyond the overlap pattern.
