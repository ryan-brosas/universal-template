<!-- capsule-v2 -->
# Batch plugin visitor — how do N plugins ride one traversal with O(1) kind dispatch and one applicability pass?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** plugins are external, slower, and can't use the rule registry — how does the analyzer host many of them per file without N traversals or per-node plugin loops?

## The plugin-host seam
**Path/Symbol:** `crates/biome_analyze/src/analyzer_plugin.rs` — `AnalyzerPlugin` trait (:50-64), `PluginVisitor` (:86-202), `BatchPluginVisitor` (:210-344), `PluginEvalResult`/`PluginDiagnosticEntry`/`PluginActionData` (:22-47).
**Signature:** `trait AnalyzerPlugin: Debug + Send + Sync { fn name(&self) -> &str; fn language(&self) -> PluginTargetLanguage; fn query(&self) -> Vec<RawSyntaxKind>; fn evaluate(&self, node: AnySyntaxNode, path: Utf8PathBuf) -> PluginEvalResult; fn applies_to_file(&self, _path: &Utf8Path) -> bool { true } }`.
**Data Shape:** `kind_to_plugins: FxHashMap<L::Kind, Vec<usize>>` (kind → indices of querying plugins; deduped via per-plugin `seen_kinds` set); `applicable: Option<Vec<bool>>` lazily filled on first qualifying Enter; results are plain data (`original_text`/`rewritten_text` strings) — the HOST converts them into TextEdits (`TextEdit::from_unicode_words`) when the signal's actions() runs.

### Decisive source
```rust
// analyzer_plugin.rs:299-317 — kind lookup first, then ONE cached applicability
// vector for all plugins, then evaluate only the interested few:
let Some(plugin_indices) = self.kind_to_plugins.get(&kind) else { return; };
let applicable = self.applicable.get_or_insert_with(|| {
    self.plugins.iter()
        .map(|p| p.applies_to_file(&ctx.options.file_path))
        .collect()
});
for &idx in plugin_indices {
    if !applicable[idx] { continue; }
    let rule_timer = profiling::start_plugin_rule(plugin.name());
    let eval_result = plugin.evaluate(node.clone().into(), ctx.options.file_path.clone());
    ...
}
```
**Flow:** construction is `unsafe new_unchecked` because plugin-returned `RawSyntaxKind`s are converted to `L::Kind::from_raw` WITHOUT validation — the caller must guarantee language match. Each entry maps eval entries into `SignalEntry { rule: SignalRuleKey::Plugin(name), category: RuleCategory::Lint, ... }` where name comes from the diagnostic SUBCATEGORY or "anonymous" (:320-325); that key is what suppression comments match against (`biome-ignore lint/plugin/myPlugin`). Signals push straight into `ctx.signal_queue.extend(...)` bypassing QueryMatcher. Both plugin visitors share SyntaxVisitor's range-skip latch (see analyzer-range-traversal capsule). Per-plugin visitors still exist but the batch form exists precisely to cut visitor-dispatch overhead (doc comment :204-209).
**Invariant:** plugin diagnostics are ALWAYS Lint-category signals keyed by subcategory-name, so they inherit line/top-level/range suppressions uniformly; a missing span defaults `text_range` to `TextRange::default()` (:185) which sorts FIRST in the heap — porters should require spans to avoid ordering surprises; unsafe construction is a language-mismatch footgun by design.
**Probe:** lib.rs tests :992-1019 pin filter gating of the reserved `plugin` group (`PLUGIN_GROUP` disabled wins over enabled; non-lint categories never run plugins); upstream biome plugins tests exercise evaluate end-to-end; no unit test covers kind_to_plugins dedup — the constructor loop above is the pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "AnalyzerPlugin BatchPluginVisitor PluginEvalResult", limit: 10, fields: ["signature", "name", "file"] });
// BatchPluginVisitor.visit analyzer_plugin.rs 268-343; new_unchecked 237-257 (line-exact)
```

## Verdict
Adopt kind→indices precomputation, single-pass lazy applicability, subcategory-keyed Lint signals riding normal suppression, and text-edit conversion at action time; adapt the plugin ABI; omit AnySyntaxNode type erasure if your plugins are in-process. Coverage caveat: filter tests exist; dedup/dispatch internals rest on source.
