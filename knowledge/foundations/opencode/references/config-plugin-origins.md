<!-- capsule-v2 -->
# Plugin origin provenance — how do merged config layers keep track of which file declared which plugin?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** After global + project + env config files merge their `plugin` arrays, how does opencode still know where each plugin came from and who wins on duplicates?

## Origin merge & dedup
**Path/Symbol:** `packages/opencode/src/config/plugin.ts` (`deduplicatePluginOrigins`, lines 64-77) + `packages/opencode/src/config/config.ts` (`mergePluginOrigins`, `pluginScopeForSource`, `resolveLoadedPlugins`, lines 101-109, 323-349).
**Signature:** `deduplicatePluginOrigins(plugins: Origin[]): Origin[]` with `Origin = { spec, source, scope: "global"|"local" }`.
**Data Shape:** `plugin_origins` is **derived state, never persisted** — `writable()` strips it before any config write-back. Each origin keeps the declaring file path and a scope inferred from it: http(s) sources → "global", `OPENCODE_CONFIG_CONTENT` → "local", paths inside the instance → "local", else "global".

### Decisive source
```ts
// config/plugin.ts:64-77 — later declarations win; order of survivors preserved
export function deduplicatePluginOrigins(plugins: Origin[]): Origin[] {
  const seen = new Set<string>()
  const list: Origin[] = []
  for (const plugin of plugins.toReversed()) {
    const spec = pluginSpecifier(plugin.spec)
    const name = spec.startsWith("file://") ? spec : parsePluginSpecifier(spec).pkg
    if (seen.has(name)) continue
    seen.add(name)
    list.push(plugin)
  }
  return list.toReversed()
}
```

**Flow:** every merge step (`global`, flag-file, project `opencode.json(c)` per directory, well-known remote, org console config, MDM plist, auto-discovered `.opencode/plugin/*.{ts,js}` globs) feeds its raw specs into `mergePluginOrigins(source, list, kind?)`; the union is re-deduped each time; both `result.plugin` (bare specs) and `result.plugin_origins` are rewritten from the deduped winners.
**Invariant:** Dedupe key = package NAME for npm specs but EXACT file URL for path specs — so an npm plugin and a same-named local checkout coexist ("keeps path plugins separate from package plugins"), while two version constraints of one package collapse to the LAST declaration. Path-like specs are resolved to absolute file URLs *at parse time*, while the declaring file is still known (`resolveLoadedPlugins`), so a later merge never reinterprets `./plugin.ts` against another directory. Auto-discovered plugin dirs `{plugin,plugins}/*.{ts,js}` are converted to file URLs by `ConfigPlugin.load(dir)` before origins are attached.
**Probe:** `packages/opencode/test/config/config.test.ts:1744-1806` — `"removes duplicates keeping higher priority (later entries)"`, `"keeps path plugins separate from package plugins"`, `"deduplicates direct path plugins by exact spec"`, `"preserves order of remaining plugins"`, plus `it.effect("loads auto-discovered local plugins as file urls")`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "deduplicatePluginOrigins mergePluginOrigins plugin origins scope", limit: 8 });
```

## Verdict
Adopt origin-provenance-through-merge as a pattern for ANY layered config (agents/MCP/permissions), the reverse-iterate-later-wins dedupe, and parse-time path resolution. Adapt the scope classifier to your own notion of global vs workspace. Omit the specific source list (well-known URLs, MDM plists) unless porting opencode's enterprise config surface.
