<!-- capsule-v2 -->
# BatchPluginVisitor — the union-bitmask fast path and lazy file-applicability cache that make N plugins one walk

**Source:** biome MIT `main@6f7774dc` (drift plane pass 13); Codebase Memory `biome`. **Question:** A porter hosting multiple external plugins per language must know why batching exists, when it's safe (unsafe fn!), and where evaluation is skipped.

## Union query set (biome_analyze/src/analyzer_plugin.rs)
**Path/Symbol:** `crates/biome_analyze/src/analyzer_plugin.rs:219-234` (struct), `:246-263` (`unsafe new_unchecked`), `:301-315` (visit hot path).
**Signature:** `new_unchecked(plugins: AnalyzerPluginSlice) -> Self` — SAFETY: "Caller must ensure all plugins target language `L`. The RawSyntaxKind values returned by each plugin's query() are interpreted as L::Kind without validation."
**Data Shape:** `plugins: Vec<(Arc<Box<dyn AnalyzerPlugin>>, SyntaxKindSet<L>)>` + `any_query: SyntaxKindSet<L>` (union) + `applicable: Option<Vec<bool>>` (lazy).

### Decisive source
```rust
// :213-218 — the reason this visitor exists
/// Instead of registering N separate `PluginVisitor` instances (one per plugin),
/// this holds all plugins together, each paired with the [SyntaxKindSet] it
/// queries. Most nodes match no plugin at all, so they are rejected with a
/// single bit test against the union of all queries.
```
```rust
// :303-312 — two-level gate + one-shot applicability computation
if !self.any_query.matches(kind) { return; }
let applicable = self.applicable.get_or_insert_with(|| {
    self.plugins.iter().map(|(plugin, _)| plugin.applies_to_file(&ctx.options.file_path)).collect()
});
```

**Flow:** Enter(node) → range check (`node.text_range_with_trivia().ordering(range).is_ne()` ⇒ set `skip_subtree`, skip until Leave of that exact node :294-299) → union bit test → lazily compute ALL plugins' applies_to_file on first qualifying node ("the file path is constant for the entire walk" :231-232 doc) → per-plugin loop: precise kind-set test AND applicable[idx] → `plugin.evaluate` under a profiling timer → entries become `SignalEntry { rule: SignalRuleKey::Plugin(subcategory-or-"anonymous"), category: RuleCategory::Lint }` pushed to `ctx.signal_queue`.
**Invariant:** Plugin signals are ALWAYS lint-category and keyed by the diagnostic's subcategory; missing subcategory falls back to `"anonymous"` (:324-328). The single-visitor `PluginVisitor` (:97-211) caches ONE tri-state `FileApplicability` (Unknown/Applicable/NotApplicable) instead of a vec. Range-formatting skip works by subtree, not per node — a porter checking ranges per-node pays O(n²) rejections.
**Probe:** `grep -c 'skip_subtree' crates/biome_analyze/src/analyzer_plugin.rs` → `14`; `grep -n 'single bit test' crates/biome_analyze/src/analyzer_plugin.rs` → `218:`; `grep -n 'get_or_insert_with' crates/biome_analyze/src/analyzer_plugin.rs` → `307:`.

## Language wiring (one line per language crate)
**Path/Symbol:** `crates/biome_js_analyze/src/lib.rs:203-214`, `crates/biome_css_analyze/src/lib.rs:202`, `crates/biome_json_analyze/src/lib.rs:151`.
**Flow:** filter plugins by `p.language() == <target>` FIRST → only then `unsafe { analyzer.add_visitor(Phases::Syntax, Box::new(BatchPluginVisitor::new_unchecked(&js_plugins))) }`, gated additionally on `filter.match_plugins()` and non-empty.
**Invariant:** Plugins run in the SYNTAX phase (before type-informed semantic phase); the unsafe block's justification comment lives at each call site ("All plugins have been verified to target JavaScript above").

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"BatchPluginVisitor new_unchecked applies_to_file","limit":5,"detail":"ids"}'
```
→ resolves both visitors + `query_kind_set` line-exact.

---
**Verdict:** ADOPT the batched-visitor shape whenever >1 plugin can be active; keep new_unchecked unsafe so language targeting stays a checked invariant at the call site.
