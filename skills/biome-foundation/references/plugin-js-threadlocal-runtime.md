<!-- capsule-v2 -->
# AnalyzerJsPlugin thread-local engine — how do you share one plugin across worker threads when the JS runtime is single-threaded?

**Source:** biome MIT `main@6f7774dc` (drift plane pass 13); Codebase Memory `biome`. **Question:** A porter embedding a scripting engine (Boa) in a parallel analyzer must know exactly what state is shared vs. per-thread, and what happens on the first evaluation inside a worker thread.

## Lazy per-thread load (analyzer_js_plugin.rs)
**Path/Symbol:** `crates/biome_plugin_loader/src/analyzer_js_plugin.rs:26-29` (`LoadedPlugin { ctx, rules }`), `:48-62` (struct: shared fs/path/`ThreadLocalCell<LoadedPlugin>`/precomputed kinds/includes), `:119-137` (`evaluate` → `get_mut_or_try_init(|| load_plugin(...))`).
**Signature:** `load(fs, path, includes)` runs ONCE on the main thread (:78-80 "to catch errors while loading, and to extract the queried kinds"); `evaluate(&self, node, path) -> PluginEvalResult` re-loads per thread.

### Decisive source
```rust
// analyzer_js_plugin.rs:46-47 — the whole reason ThreadLocalCell exists
/// A JS analyzer plugin.
/// As the JS engine is intended to run in single thread, plugins are lazily loaded in each thread
/// just before executing it.
```
```rust
// :120-122 — first evaluate in THIS thread pays the full module load
let mut plugin = match self.loaded.get_mut_or_try_init(|| load_plugin(self.fs.clone(), &self.path)) {
    Ok(plugin) => plugin,
    Err(err) => return PluginEvalResult { entries: vec![/* one "Could not load the plugin" diagnostic */] },
};
```

**Flow:** main-thread `load()` imports the module once to fail fast AND harvests the union of queried syntax kinds (`kinds.sort_unstable_by_key(|k| k.0); kinds.dedup()` :82-89) because `query()` may be called from threads that haven't loaded (:53-55 doc) → per-node `evaluate`: lazy-init the thread's own Boa context + rule handles → downcast `AnySyntaxNode` to `JsSyntaxNode` (failure = one diagnostic, never panic) → filter rules whose `kinds.contains(&kind)` → `ctx.call_function(&rule.run, JsValue::undefined(), [ast])`.
**Invariant:** A failed per-thread load becomes a diagnostic entry, NOT an error — analysis continues with every node reporting. And the diagnostics drain is unconditional: `pull_diagnostics()` runs BEFORE the error check so a panicking rule can't leak its diagnostics into the next rule (:162-164 comment "Drain the diagnostics even on errors"). Porters who drain after the success check cross-contaminate rule output.

## Rule harvesting contract (js_runtime/src/context.rs:139-198)
**Path/Symbol:** `crates/biome_js_runtime/src/context.rs:139-198` (`load_rules`).
**Data Shape:** Every namespace export that has object props `query` + function `run` becomes a `JsPluginRule { name: export_name, kinds: Vec<JsSyntaxKind>, run }`; other exports are ignored ("so plugins can export helpers").
**Invariant:** `query.type` must be the string `"ast"` else TypeError; each kind string goes through `syntax_kind_from_ast_name` with unknown names raising `"queries an unknown syntax kind"` at LOAD time (:172-179) — bad queries never survive to evaluate. Empty rule set rejects the whole plugin at load: analyzer_js_plugin.rs:36-40 `"The plugin must export at least one rule created with defineRule()"`.

## AST exposure shape (test-pinned)
The matched node crosses to JS as prototype-getter views, not eagerly-cast objects — test `passes_the_matched_node_to_run` pins the exact tuple `JS_MODULE|function|false|false` (getter exists / not own property / unknown fields not exposed), :278-320.
**Probe:** `grep -c 'get_mut_or_try_init' crates/biome_plugin_loader/src/analyzer_js_plugin.rs crates/biome_plugin_loader/src/thread_local.rs` → `1` + `1`; `grep -n 'Drain the diagnostics even on errors' crates/biome_plugin_loader/src/analyzer_js_plugin.rs` → `162:`; `grep -c '#\[test\]' crates/biome_plugin_loader/src/analyzer_js_plugin.rs` → `13`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"AnalyzerJsPlugin load_plugin LoadedPlugin thread","limit":5,"detail":"ids"}'
```
→ resolves `biome.crates.biome_plugin_loader.src.analyzer_js_plugin.load_plugin` (:31-43) line-exact.

---
**Verdict:** ADOPT the thread-local-lazy pattern for any single-threaded engine embedded in a parallel pipeline; the precomputed-kinds trick is mandatory (query() must be thread-safe before init).
