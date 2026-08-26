<!-- capsule-v2 -->
# Plugin runtime-config store — how do you persist per-plugin enablement and settings across two scopes without a database?

**Source:** oh-my-pi (MIT) `main@2b66ee69f249`; Codebase Memory `oh-my-pi`. **Question:** Where does plugin enabled/disabled state, feature selection, and settings live, and how do project-level overrides layer on top of user-global state?

## Connected graph-selected seam
**Path/Symbol:** `packages/coding-agent/src/extensibility/plugins/manager.ts:PluginManager` config plane — `#ensureConfigLoaded` (:141-146, fan-in 15), `#saveRuntimeConfig` (:148-151), `#loadProjectOverrides` (:153-162), `getPluginSettings` (:893-901), doctor self-heal `#fixMissingPlugin`/`#removeInvalidFeature`/`#removeOrphanedConfig` (:1090-1129); schema `plugins/types.ts:PluginRuntimeConfig` (:141-146); normalizer `plugins/runtime-config.ts:normalizePluginRuntimeConfig` (9L whole).
**Signature:** store = `<pluginsDir>/omp-plugins.lock.json`: `{ plugins: Record<name, {version, enabledFeatures: string[]|null, enabled}>, settings: Record<name, Record<key, unknown>> }`; overrides = `<project>/.omp/plugin-overrides.json`: `{ disabled?: string[], features?, settings? }`.
**Data Shape:** three-layer merge for reads: runtime lockfile (user) ← project overrides; features resolve as `projectOverrides.features?.[name] ?? runtimeState.enabledFeatures`; enabled resolves as `runtimeState.enabled && !projectOverrides.disabled?.includes(name)`.

### Decisive source
```ts
async #ensureConfigLoaded(): Promise<PluginRuntimeConfig> {
	if (!this.#runtimeConfig) {                       // lazy per-instance singleton;
		this.#runtimeConfig = await this.#loadRuntimeConfig(); // ENOENT + parse-fail both
	}                                                 // normalize to { plugins:{}, settings:{} }
	return this.#runtimeConfig;
}
async #saveRuntimeConfig(): Promise<void> {
	await this.#ensureConfigLoaded();                 // write-through of the SAME object
	await Bun.write(getPluginsLockfile(), JSON.stringify(this.#runtimeConfig, null, 2));
}
// getPluginSettings: return { ...global, ...project };  // shallow spread, project wins
```
**Flow:** every mutator (`install`, `uninstall`, `link`, `setEnabled`, `setEnabledFeatures`, `setPluginSetting`, `deletePluginSetting`) awaits the lazy load, mutates the in-memory object, writes the whole file. Uninstall deletes BOTH `config.plugins[name]` and `config.settings[name]`. `doctor({fix})` self-heals in three directions: dep-without-tree → `bun install`; tree-less config-only entry → delete orphaned plugin+settings keys; stale feature name → filter out of enabledFeatures — each reported as a DoctorCheck with `fixed` flag.
**Invariant:** the lockfile is write-through cache-of-truth, not a journal; corrupt JSON degrades to empty (warn + normalize), never throws into callers. Feature `null` means "manifest defaults", distinct from `[]` ("explicitly none"). Project overrides never rewrite global state — they are applied at read time.
**Probe:** direct-test seam: `test/plugin-install-validation.test.ts` asserts lock contents after rollback (`lock.plugins["broken-plugin"]` equals v1 state :265-266, :343-344); anchor-grep at pin: `if (!this.#runtimeConfig) {` manager.ts:142.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "ensureConfigLoaded saveRuntimeConfig PluginManager" });
```

## Verdict
Adopt: one JSON lockfile with lazy-load/write-whole semantics plus a read-time project override layer; normalize-on-read so legacy/corrupt shapes degrade to empty. Adapt: your own config-dir resolver behind the same accessor seam. Omit: doctor's bun-specific fix command; keep the check-report-fix triple shape.
