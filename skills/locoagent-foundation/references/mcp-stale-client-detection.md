<!-- capsule-v2 -->
# Stale-client detection on reload — how does /reload-plugins decide which MCP connections to drop without disconnecting user-configured servers?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What staleness rules apply per scope, and what config hash makes "the server changed" decidable?

## Scope-scoped removal + scope-excluded sorted-key hash
**Path/Symbol:** `src/services/mcp/utils.ts`: `hashMcpConfig` (:151-169), `excludeStalePluginClients` (:171-224), exclusion helpers (:109-149).
**Signature:** stale predicate: `const fresh = configs[c.name]; if (!fresh) return c.config.scope === 'dynamic'; return hashMcpConfig(c.config) !== hashMcpConfig(fresh)`.
**Data Shape:** hash = sha256 of JSON.stringify with RECURSIVELY SORTED keys and `scope` stripped, first 16 hex chars.

### Decisive source
```ts
// Stable hash of an MCP server config for change detection on /reload-plugins.
// Excludes `scope` (provenance, not content — moving a server from .mcp.json
// to settings.json shouldn't reconnect it). Keys sorted so {a:1,b:2} and
// {b:2,a:1} hash the same.
//
// The removal case is scoped to 'dynamic' so /reload-plugins can't
// accidentally disconnect a user-configured server that's just temporarily
// absent from the in-memory config (e.g. during a partial reload). The
// config-changed case applies to all scopes — if the config actually changed
// on disk, reconnecting is what you want.
for (const s of stale) {
  tools    = excludeToolsByServer(tools, s.name)
  commands = excludeCommandsByServer(commands, s.name)
  resources = excludeResourcesByServer(resources, s.name)
}
```

**Flow:** reload computes fresh configs → classify clients: missing-from-config + dynamic ⇒ stale; hash mismatch at ANY scope ⇒ stale → atomically strip each stale server's tools/commands/resources alongside its client → caller disconnects the returned stale list (clearServerCache).
**Invariant:** Absence only removes dynamic-scope servers; content change removes any scope. Scope must be excluded from the hash or moving a config between files causes pointless reconnects; key-sorting is required because insertion order differs between parse paths.
**Probe:** `grep -n 'configs\[c.name\]' src/services/mcp/utils.ts` (`201:`) and `grep -n "c.config.scope === 'dynamic'" src/services/mcp/utils.ts` (`202:`) and `grep -n "digest('hex').slice(0, 16)" src/services/mcp/utils.ts` (`168:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "excludeStalePluginClients", limit: 5 });
```

## Verdict
Adopt the two-rule staleness classifier and canonical hash. Adapt to your reload triggers. Omit UI surfacing of stale lists.
