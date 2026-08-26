<!-- capsule-v2 -->
# Config two-scope model — how do global defaults, trusted project overrides, legacy keys, and env kill-switches compose?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** Settings merge over defaults from `~/.pi/agent/fovea.json` and trusted `<repo>/.pi/fovea.json` — what is the precedence ladder, how do v0.10 booleans migrate, and why can a project override stay effective while its GLOBAL default is being edited?

## Layered applyPartial with enum fallbacks and atomic saves
**Path/Symbol:** `src/core/config.ts:applyPartial/loadFoveaConfig/loadFoveaConfigForScope/saveFoveaConfig/buildPartialFromId/BOUNDS` (:88-229); UI scope switch `src/ui/settings.ts` (Ctrl+G swaps display+save destination).
**Signature:** `loadFoveaConfig(scopes): FoveaConfig`; `loadFoveaConfigForScope(scopes, "global"|"project")`; `saveFoveaConfig(scopes, partial): {scope, path}` (tmp-write + rename).
**Data Shape:** Bounded knobs (`BOUNDS`): sync.budget 128..8192, tools.defaultBudget 256..16000, grepAugmentBudget 256..8192, steerThreshold 0.02..8. Unknown enum values fall back per-field; malformed JSON/array roots read as {}.

### Decisive source
```ts
let config = applyPartial(DEFAULT_FOVEA_CONFIG, readConfigFile(globalFoveaConfigPath(scopes.agentDir)));
if (includeProject) config = applyPartial(config, readConfigFile(projectFoveaConfigPath(scopes.cwd)));
// Environment override mirrors pi-fabric's PI_* precedence over stored values:
const off = process.env.FOVEA_TURN_SYNC;
if (off === "off" || off === "0" || off === "false")
  config = { ...config, sync: { ...config.sync, mode: "disabled" } };
// Legacy migration — explicit key ALWAYS beats legacy:
mode: enumValue(sync.mode, SYNC_MODES,
  typeof sync.enabled === "boolean" ? (sync.enabled ? "enabled" : "disabled") : base.sync.mode),
grepMode: enumValue(tools.grepMode, GREP_MODES,
  typeof tools.replaceGrep === "boolean" ? (tools.replaceGrep ? "replace" : "off") : base.tools.grepMode),
```

**Flow:** defaults ← global file ← (trusted-only) project file ← env kill-switch. Per-scope loads exist so the settings UI can show global defaults while a project override remains effective (Ctrl+G picks the save destination; untrusted projects refuse project loads/saves). Saves deep-merge the partial into the target file and write atomically (`${path}.tmp-${pid}` → rename); settings UI builds partials from dotted ids via `buildPartialFromId`.
**Invariant:** Project overrides require TRUST (never parse an untrusted repo's config as instructions); env always wins over stored values; numeric clamps bound every budget knob regardless of file contents; explicit modern keys dominate legacy booleans.
**Probe:** `tests/config.test.ts` — "loads global defaults separately from trusted project overrides"; "migrates legacy sync enabled booleans and prefers an explicit mode"; "migrates legacy replaceGrep booleans"; "rejects unknown modes and clamps the augment budget" (99999 → 8192); "lets FOVEA_TURN_SYNC=off override hidden mode".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "applyPartial loadFoveaConfig saveFoveaConfig", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the layered resolution order, trust-gated project scope, bounded knobs, legacy-key dominance rules, atomic tmp-rename saves, and dotted-id partial builder. Adapt key names/bounds. Omit the fabric-mirror commentary.
