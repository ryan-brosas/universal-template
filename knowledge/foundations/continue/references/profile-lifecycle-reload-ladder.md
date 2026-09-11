<!-- capsule-v2 -->
# Profile reload ladder — who recompiles the config, when, and why can loadConfig never reject?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How do you cache a config compile across consumers, single-flight concurrent loads, and route file-watch events into reloads without ever throwing to callers?

## Three-slot cache + never-rejecting loader + cascade reloads
**Path/Symbol:** `core/config/ProfileLifecycleManager.ts` (whole class 28–142), `core/config/profile/LocalProfileLoader.ts:doLoadConfig` (43–67), `core/config/ConfigHandler.ts:reloadConfig` (237–283), `core/core.ts` watch chains (247–257, 857–895).
**Signature:** `loadConfig(additionalContextProviders: IContextProvider[], forceReload = false): Promise<ConfigResult<ContinueConfig>>` ; `reloadConfig(reason: string): Promise<...>` ; `getSerializedConfig(...): Promise<ConfigResult<BrowserSerializedContinueConfig>>`.
**Data Shape:** three private slots — `savedConfigResult`, `savedBrowserConfigResult`, `pendingConfigPromise`. `ConfigResult<T> = { config?: T; errors: ConfigValidationError[]; configLoadInterrupted: boolean }`.

### Decisive source
```ts
// ProfileLifecycleManager.loadConfig — single-flight + total-error capture
if (!forceReload) {
  if (this.savedConfigResult) return this.savedConfigResult;
  else if (this.pendingConfigPromise) return this.pendingConfigPromise;   // join in-flight load
}
this.pendingConfigPromise = new Promise((resolve) => { void (async () => {
  let result: ConfigResult<ContinueConfig>;
  try { result = await this.profileLoader.doLoadConfig(); }
  catch (e) {                                   // high-level errors ONLY (invalid json/yaml, fs)
    Logger.error(e, { context: "profile_config_loading" });
    result = { errors: [{ fatal: true, message }], config: undefined, configLoadInterrupted: true };
  }
  if (result.config) result.config.contextProviders = (result.config.contextProviders ?? [])
    .concat(additionalContextProviders);        // registered providers injected AFTER compile
  resolve(result);
})(); });
this.savedConfigResult = await this.pendingConfigPromise;   // settle slot before returning
this.pendingConfigPromise = undefined;

// ConfigHandler.reloadConfig — cascade hygiene
for (const profile of this.profiles) if (profile !== current) profile.clearConfig();
const out = await this.currentProfile.reloadConfig(this.additionalContextProviders);
this.notifyConfigListeners(out); this.initter.emit("init");
```

**Flow:** consumers call loadConfig → cache hit returns saved; miss joins pending promise; forceReload (reloadConfig path) clears all three slots first → profileLoader.doLoadConfig compiles → ANY throw becomes a fatal ConfigResult inside the loader (loadConfig never rejects) → context providers appended → saved. ConfigHandler clears OTHER profiles' caches, reloads current, notifies listeners, emits init. File watches: colocated rules.md create/delete mutate `CodebaseRulesCache` FIRST (upsert/remove) THEN call reloadConfig; startup does `cache.refresh(ide).catch(log).then(() => reloadConfig("Initial codebase rules post-walkdir/load reload"))` fire-and-forget.
**Invariant:** at most one compile in flight per manager; callers always receive a ConfigResult (errors are data, not exceptions); a GUI poll via getSerializedConfig uses its OWN browser-slot cache and never forces a recompile; rule-cache mutation strictly precedes the reload it triggers.
**Probe:** no direct suite at this pin (runner block). Source-pinned observables: LocalProfileLoader passes pre-read override content to bypass WSL `fs.readFileSync` (#10450) and back-fills `description.errors`/title from `result.configName`; core.ts:253 swallows refresh errors but still reloads.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "ProfileLifecycleManager reloadConfig clearConfig", limit: 8 });
await mcp.codebase_memory.trace_path({ project: "continue", function_name: "continue.core.config.ConfigHandler.ConfigHandler.reloadConfig", direction: "inbound", depth: 2 });
// observed inbound: profile switch (:230), rules-cache chains (core.ts), IDE config-related file events
```

## Verdict
Adopt the three-slot cache with pending-promise joining and catch-to-ConfigResult conversion for any hot-recompiled resource; adapt provider injection point and listener emission to your host; omit multi-profile cascade clearing unless you actually serve multiple profiles from one process.
