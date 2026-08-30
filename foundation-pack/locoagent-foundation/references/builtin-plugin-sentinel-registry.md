<!-- capsule-v2 -->
# builtin plugin sentinel registry — how do in-binary plugins join a marketplace-shaped plugin system without a filesystem?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Your plugin system is marketplace-shaped (`{name}@{marketplace}` IDs, filesystem paths, enable/disable settings) — how do you admit compiled-in plugins into it cleanly?

## builtinPlugins.ts: `@builtin` marketplace sentinel + path-sentinel LoadedPlugin
**Path/Symbol:** `src/plugins/builtinPlugins.ts`:`BUILTIN_MARKETPLACE_NAME` `:23`, `registerBuiltinPlugin` `:28-32`, `isBuiltinPluginId` `:37-39`, `getBuiltinPlugins` enabled/disabled split `:57-102`, `skillDefinitionToCommand` source-mapping comment `:145-149`, `src/plugins/bundled/index.ts` empty scaffolding `initBuiltinPlugins` `:20-23`. Snapshot caveat: no upstream wiring calls `initBuiltinPlugins()` yet (grep for the name resolves only this file) — port the registry pattern, not a working feature.
**Signature:** `registerBuiltinPlugin(definition: BuiltinPluginDefinition): void`; `isBuiltinPluginId(pluginId: string): boolean`; `getBuiltinPlugins(): { enabled: LoadedPlugin[]; disabled: LoadedPlugin[] }`; `clearBuiltinPlugins(): void` (tests).
**Data Shape:** Registry keyed by bare name; public ID = `` `${name}@builtin` ``. `LoadedPlugin.path = 'builtin'` — a SENTINEL string, not a real directory. Enabled-state precedence: user setting > `defaultEnabled ?? true`.

### Decisive source
```ts
// :70-76 — precedence ladder
const pluginId = `${name}@${BUILTIN_MARKETPLACE_NAME}`
const userSetting = settings?.enabledPlugins?.[pluginId]
// Enabled state: user preference > plugin default > true
const isEnabled =
  userSetting !== undefined
    ? userSetting === true
    : (definition.defaultEnabled ?? true)
// :85-89 — the filesystem-shaped lie, documented
path: BUILTIN_MARKETPLACE_NAME, // sentinel — no filesystem path
source: pluginId,
repository: pluginId,
enabled: isEnabled,
isBuiltin: true,
```

**Flow:** startup calls `initBuiltinPlugins()` (currently zero registrations — scaffolding) → registered definitions land in a Map → plugin aggregation asks `getBuiltinPlugins()` → availability-filtered (`isAvailable()`) entries are shaped as normal LoadedPlugins with sentinel path/repo → downstream UI/settings treat them like any marketplace plugin → skills from ENABLED plugins convert to Commands with `source: 'bundled'`.
**Invariant:** Integration-by-shape-imitation: instead of special-casing builtins through the whole plugin pipeline, produce objects that satisfy the existing contract and mark provenance with two sentinels (ID suffix `@builtin` for identity checks via `endsWith`, `path='builtin'` for anything that would touch disk). The skill→Command converter deliberately maps to `'bundled'` NOT `'builtin'` because Command.source has an existing meaning for `'builtin'` (hardcoded slash commands); the user-toggleable aspect lives on `LoadedPlugin.isBuiltin` — one concept, TWO fields, each respecting its own enum's vocabulary.
**Probe:** Deterministic pins: `grep -n "endsWith(\`@\${BUILTIN_MARKETPLACE_NAME}\`)" src/plugins/builtinPlugins.ts` → `38:`; `grep -n 'sentinel — no filesystem path' src/plugins/builtinPlugins.ts` → `85:`; `grep -n 'user preference > plugin default' src/plugins/builtinPlugins.ts` → `72:`; `grep -cn "source: 'bundled'" src/plugins/builtinPlugins.ts` → `1` (:149).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "builtinPlugins BUILTIN_MARKETPLACE_NAME getBuiltinPlugins", limit: 10 });
```

## Verdict
Adopt sentinel-ID + sentinel-path shape imitation when bolting a new provider onto an existing extension system. Adapt the marketplace suffix and precedence ladder to your settings schema. Omit the empty scaffolding file itself (port the pattern, not the placeholder).
