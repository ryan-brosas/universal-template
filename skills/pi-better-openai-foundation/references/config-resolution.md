<!-- capsule-v2 -->
# Config resolution — layer project/global/default, normalize model keys, clamp numerics

**Source:** pi-better-openai (MIT, `main@86814e9047996abba08e4c907e23286329196fe0`); Codebase Memory `pi-better-openai`. **Question:** How does an extension resolve a typed config from two JSON files plus defaults, while validating enums, normalizing model keys, and clamping numeric settings to safe ranges — without losing unknown fields on write?

## Layered config resolution
**Path/Symbol:** `src/config.ts:resolveConfig` (768–876); helpers `configPaths` (559–564), `parseModelKey` (566–573), `normalizeModelKeys` (575–583), `parseModels` (585–591), `readRawConfig` (593–603), `readConfig` (611–717), `applySettingToRawConfig` (725–751), `writeConfig` (753–761).
**Signature:** `resolveConfig(cwd: string): ResolvedConfig`; `configPaths(cwd, home?, env?) → { project, global }`; `parseModelKey(value: string): SupportedModel | undefined`; `applySettingToRawConfig(current, id, rawValue, context?) → Record<string, unknown>`.
**Data Shape:** `ResolvedConfig` carries `configPath`, `projectConfigPath`, `globalConfigPath`, `projectConfigExists`, `globalConfigExists`, `persistState`, `active`, `desiredActive`, `supportedModels: SupportedModel[]`, and required sub-configs `usage`/`footer`/`image`/`websearch`/`live`/`pets`. Project config is `.pi/extensions/<CONFIG_BASENAME>`; global is `<piAgentDir>/extensions/<CONFIG_BASENAME>`. `SupportedModel = { provider, id }`.

### Decisive source
```ts
// configPaths: project overrides global; global dir honors PI_CODING_AGENT_DIR (tilde-expanded)
project: join(cwd, ".pi", "extensions", CONFIG_BASENAME),
global: join(piAgentDir(env, home), "extensions", CONFIG_BASENAME),

// parseModelKey: require a '/' with non-empty both sides, else undefined
const slash = key.indexOf("/");
if (slash <= 0 || slash === key.length - 1) return undefined;

// resolveConfig merge: defaults <- global <- project (project wins)
const merged = { ...DEFAULT_CONFIG, ...globalConfig, ...projectConfig };
const selectedPath = projectConfigExists ? paths.project : paths.global;

// numeric clamping pattern (usage.refreshIntervalMs example)
refreshIntervalMs: Math.max(15_000, Math.min(10 * 60_000,
  projectConfig.usage?.refreshIntervalMs ?? globalConfig.usage?.refreshIntervalMs ?? DEFAULT_USAGE_CONFIG.refreshIntervalMs)),

// writeConfig preserves unknown fields: callers spread readRawConfig first
writeConfig(path, { ...readRawConfig(path), active, desiredActive });
```

**Flow:** (1) compute project/global paths; (2) `ensureConfigFile` writes a default global config only if neither exists; (3) read both raw files, each validated field-by-field with type checks and enum membership (`FOOTER_MODES`, `IMAGE_SAVE_MODES`, `PET_STATES`, etc.); (4) shallow-merge defaults → global → project; (5) `desiredActive = merged.desiredActive ?? merged.active ?? false`; (6) clamp every numeric field to its safe range; (7) `parseModels` normalizes the supported-model list (invalid entries dropped). `applySettingToRawConfig` routes a setting id through a descriptor's `parse` into the right section, with a special `fast.enabled` branch that only writes `active`/`desiredActive` when `persistState` is set.

**Invariant:** project config always wins over global; invalid enum values and non-conforming types are silently dropped (never crash); every numeric setting is clamped to its documented safe range; writing never destroys unknown/extra fields because callers spread `readRawConfig` first.

**Probe:** `tests/config.test.ts` — `parses and normalizes model keys` (`parseModelKey("openai/gpt-5.5")` → `{provider:"openai",id:"gpt-5.5"}`; `parseModelKey("bad")` → undefined; `normalizeModelKeys(["openai/gpt-5.5","bad",42])` → `["openai/gpt-5.5"]`); `migrates legacy Responses image models to the standalone image model` (resolveConfig maps `openai-codex/gpt-5.5` → `gpt-image-2`); `uses PI_CODING_AGENT_DIR for global config and expands a home-relative path`; `preserves unknown config fields while writing updates`; `clamps numeric usage, image, and pet settings` (`refreshIntervalMs:1` → 15000, `image.timeoutMs:1` → 30000, `pets.sizeCells:99` → 16). Coverage caveat: `tests/` is excluded from the index by design (`fast-pattern`), so these probes are source-grounded from the on-disk test file, not graph-covered.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "resolveConfig parseModelKey normalizeModelKeys applySettingToRawConfig writeConfig", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the defaults → global → project merge order, the field-by-field type/enum validation, the model-key normalization, the numeric clamping, and the non-destructive write pattern. Adapt the config basename, the default model list, and the safe numeric ranges to the host. Omit the settings-picker descriptor UI unless a target needs it.
