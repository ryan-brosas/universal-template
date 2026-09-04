<!-- capsule-v2 -->
# Plugin lifecycle in the workspace server — load-on-settings, per-project caches, and the error→hard-fail gate

**Source:** biome MIT `main@6f7774dc` (drift plane pass 13); Codebase Memory `biome`. **Question:** When do plugins actually load, how are they cached per project, and which plugin errors abort a session vs. surface as diagnostics?

## Load timing (biome_service/src/workspace/server.rs)
**Path/Symbol:** `crates/biome_service/src/workspace/server.rs:1651-1671` (`load_plugins`), `:1676-1685` (`get_analyzer_plugins_for_project`), `:2599-2616` (update_settings call site), `:2713-2716` (unload_folder retention).
**Signature:** `load_plugins(&self, base_path: &Utf8Path, plugins: &Plugins) -> Vec<PluginDiagnostic>`; cache is `plugin_caches: Arc<HashMap<Utf8PathBuf, PluginCache>>` (:120) keyed by project base path.

### Decisive source
```rust
// :2599-2610 — plugins (RE)LOAD inside update_settings, and ANY Error-severity
// diagnostic aborts the whole settings update
let plugin_diagnostics = self.load_plugins(
    &workspace_directory.clone().unwrap_or_default(),
    &settings.as_all_plugins(),
);
let has_errors = plugin_diagnostics.iter().any(|d| d.severity() >= Severity::Error);
if has_errors {
    return Err(WorkspaceError::plugin_errors(plugin_diagnostics));
}
```

**Flow:** settings update → fresh `PluginCache::default()` → for each configured entry `BiomePlugin::load(fs, path, base_path, includes)`: Ok ⇒ `insert_plugin(path, plugin)` (keyed by CONFIG path string, not resolved path); Err ⇒ collected into returned diagnostics — then the cache is inserted EVEN IF some loads failed (`self.plugin_caches.pin().insert(...)` runs unconditionally :1668-1670). Consumers (`pull_actions` :1288, `pull_diagnostics` :1528, code actions :3363) call `get_analyzer_plugins_for_project(source_path, settings.get_plugins_for_path(path))`; missing cache = empty vec, NOT an error.
**Invariant:** Two different plugin lists exist by design: `as_all_plugins()` (base + every override pattern, used at LOAD time so everything gets cached) vs `get_plugins_for_path(path)` (only patterns whose glob includes the file — used at QUERY time for filtering). A porter loading only the path-filtered set breaks override-declared plugins that later match other files. Unloading a project RETAINS caches whose key does NOT start with the project path (`retain(|path, _| !path.starts_with(&project_path))`) — prefix semantics, not equality.

## Path-scoped config resolution (biome_service/src/settings.rs)
**Path/Symbol:** `crates/biome_service/src/settings.rs:479-491` (`get_plugins_for_path`), `:493-507` (`as_all_plugins`).
**Data Shape:** Both return `Cow<'_, Plugins>`; override matches APPEND to base (duplicates possible — deduped downstream by `PluginCache::get_analyzer_plugins`'s `seen: FxHashSet` on config-path strings).
**Probe:** `grep -c 'fn get_analyzer_plugins_for_project\|fn load_plugins' crates/biome_service/src/workspace/server.rs` → `2`; `grep -n 'return Err(WorkspaceError::plugin_errors' crates/biome_service/src/workspace/server.rs` → `2610:` (SOLE hit — the only hard-abort; a bare `grep -n 'Severity::Error'` is the WRONG probe, first hits are unrelated config-parse helpers at :197/:207); `grep -n 'seen.insert(plugin_path)' crates/biome_plugin_loader/src/plugin_cache.rs` → `34:`. Query-time consumers (:1288 pull_actions, :1528 pull_diagnostics, :3363 code actions) do NOT abort — they propagate per-call via `.map_err(WorkspaceError::plugin_errors)?` (4 `plugin_errors` sites total, 1 return-Err + 3 map_err).

## Cache lookup contract (biome_plugin_loader/src/plugin_cache.rs)
**Path/Symbol:** `crates/biome_plugin_loader/src/plugin_cache.rs:36-46`.
**Flow:** `map.iter().find(|(path, _)| path.ends_with(path_buf.as_path()))` — cache keys are RESOLVED absolute paths (from BiomePlugin::load's return), lookup keys are CONFIG paths; matching is suffix-`ends_with`, first hit wins.
**Invariant:** papaya (concurrent) HashMap + FxBuildHasher; `get_analyzer_plugins` accumulates ALL failing configs into one `Vec<PluginDiagnostic>` returned as Err only after the full sweep (batch-fail, not fail-fast).

---
**Verdict:** ADOPT: reload-on-settings-change, per-project cache maps, hard-fail only on Error severity. The dual list (all vs per-path) and ends_with cache matching are the porting traps.
