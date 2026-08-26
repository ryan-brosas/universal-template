<!-- capsule-v2 -->
# AnalyzerGritPlugin — how a GritQL pattern file becomes diagnostics + fixes, and the position-paired action contract

**Source:** biome MIT `main@6f7774dc` (drift plane pass 13); Codebase Memory `biome`. **Question:** A porter wiring declarative query plugins must reproduce the effect→action conversion and the diagnostic/action POSITION pairing (not id pairing).

## Compile-time shape (analyzer_grit_plugin.rs:35-58)
**Path/Symbol:** `crates/biome_plugin_loader/src/analyzer_grit_plugin.rs:42-51` (`CompilePatternOptions` + extra built-in), `:62-72` (`language()` maps Grit target → `PluginTargetLanguage`), `:74-88` (`query()` returns the WHOLE root KIND_SET).
**Signature:** `load(fs: &dyn FileSystem, path, includes)` compiles the `.grit` source with one extra built-in predicate injected: `register_diagnostic(span, message, severity?, fix_kind?)`.

### Decisive source
```rust
// :74-79 — Grit plugins query EVERY node kind of their language (unlike JS plugins' precise kinds)
fn query(&self) -> Vec<RawSyntaxKind> {
    match self.language() {
        PluginTargetLanguage::JavaScript => AnyJsRoot::KIND_SET.iter().map(|k| k.to_raw()).collect(),
        ...
```

**Flow:** `evaluate` re-wraps the single node as a synthetic whole-file `AnyParse::Node(NodeParse::new(root, vec![]))` (:124) so Grit sees a complete document → `grit_query.execute_optimized(file)` → three output lanes merged in order: logs (verbose diagnostics, "Log entries never consume actions" :129) → rewrite effects filtered to `GritQueryEffect::Rewrite` becoming `PluginActionData` with `Applicability::MaybeIncorrect` default → REAL diagnostics paired with actions **by position** via `action_iter.next()` (:157-171): "Pair each real diagnostic with its action by position."
**Invariant:** Diagnostic↔action pairing is positional; if Grit emits an action without a matching diagnostic, that action is SILENTLY DROPPED (drain leaves it unconsumed). The applicability from the paired diagnostic OVERWRITES the action's default. Any missing span on ANY diagnostic appends ONE aggregate warning telling users diagnostics were shown without context (:174-191) — not per-diagnostic warnings.

## register_diagnostic built-in (:213-292)
**Path/Symbol:** `crates/biome_plugin_loader/src/analyzer_grit_plugin.rs:221-228` arity check, `:230-233` span = last binding's `text_trimmed_range()`, `:254-266` severity parse, `:268-284` fix_kind map.
**Data Shape:** 2 required args (`span`, `message`) + 2 optional (`severity` ∈ hint|info|warn|error defaulting Error; `fix_kind` ∈ safe→Always | unsafe→MaybeIncorrect, anything else = hard error). Message resolution ladder: Constant → Snippets fold (concatenated) → last-binding text → `"(no message)"`.
**Invariant:** Returns `Ok(span_node.clone())` — the span node itself becomes the resolved pattern so the predicate can participate in further matching.

## Direct tests (:305-363)
Glob semantics live here, NOT in biome_glob: negated globs exclude (`applies_with_negated_glob_exclusion` :335), relative globs do NOT match absolute paths by design (`glob_does_not_match_absolute_paths_without_prefix` :346, comment "Users should use `**/src/**/*.ts`"), empty includes matches NOTHING (:357 — pins the doc-comment contract).
**Probe:** `grep -c 'Applicability::MaybeIncorrect' crates/biome_plugin_loader/src/analyzer_grit_plugin.rs` → `3` (:151 rewrite-effect default, :269 no-fix_kind default, :276 unsafe arm); `grep -n 'Pair each real diagnostic' crates/biome_plugin_loader/src/analyzer_grit_plugin.rs` → `157:`; `grep -n 'execute_optimized' crates/biome_plugin_loader/src/analyzer_grit_plugin.rs` → `127:`; `grep -c '#\[test\]' crates/biome_plugin_loader/src/analyzer_grit_plugin.rs` → `7`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"AnalyzerGritPlugin register_diagnostic compile_pattern","limit":5,"detail":"ids"}'
```

---
**Verdict:** ADOPT for declarative-rule hosting; the positional pairing and silent-action-drop are the two behaviors porters get wrong.
