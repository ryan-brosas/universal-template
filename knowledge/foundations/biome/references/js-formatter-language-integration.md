<!-- capsule-v2 -->
# JsFormatLanguage integration — how does a language plug options, transform, range eligibility and embedded ranges into the generic format_node?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What must a porter implement to make `biome_formatter::format_node` work for a new language, and what is the exact contract of each FormatLanguage method as JS implements it?

## The FormatLanguage impl + public entry wrappers
**Path/Symbol:** `crates/biome_js_formatter/src/lib.rs:521-587` (`JsFormatLanguage` struct + impl), `lib.rs:600-652` (`format_range` / `format_node` / `format_sub_tree` wrappers). *(Ranges +1 after pass-15's `mod astro;` insert; integration unchanged — the same drift added five `format_astro_template` tests in this file's test module.)*
**Signature:** `impl FormatLanguage for JsFormatLanguage { type SyntaxLanguage = JsLanguage; type Context = JsFormatContext; type FormatRule = FormatJsSyntaxNode; fn transform(&self, root) -> Option<(SyntaxNode, TransformSourceMap)>; fn is_range_formatting_node(&self, node) -> bool; fn create_context(self, root, source_map, delegate_fmt_embedded_nodes) -> Self::Context; }`.
**Data Shape:** `JsFormatLanguage { options: JsFormatOptions, embedded_node_ranges: Vec<TextRange> }` — ranges captured up-front from the caller's parse of embedded languages.

### Decisive source
```rust
// lib.rs:553-567 — range-formatting eligibility whitelist
fn is_range_formatting_node(&self, node: &JsSyntaxNode) -> bool {
    let kind = node.kind();
    // Do not format variable declaration nodes, format the whole statement instead
    if matches!(kind, JsSyntaxKind::JS_VARIABLE_DECLARATION) { return false; }
    AnyJsStatement::can_cast(kind)
        || AnyJsDeclaration::can_cast(kind)
        || matches!(kind,
            JsSyntaxKind::JS_DIRECTIVE | JsSyntaxKind::JS_EXPORT | JsSyntaxKind::JS_IMPORT)
}
// lib.rs:616-627 — entry decides delegation by EMPTINESS of the ranges vec
pub fn format_node(options, root, embedded_node_ranges: Vec<TextRange>)
    -> FormatResult<Formatted<JsFormatContext>> {
    let delegate_fmt_embedded_nodes = !embedded_node_ranges.is_empty();
    biome_formatter::format_node(root,
        JsFormatLanguage::new(options).with_embedded_node_ranges(embedded_node_ranges),
        delegate_fmt_embedded_nodes)
}
```

**Flow:** host calls `format_node(options, root, ranges)` → wrapper derives `delegate_fmt_embedded_nodes` from emptiness → `create_context` builds `Comments::from_node(root, &JsCommentStyle, source_map)` then attaches options/source-map and — only when delegating — the embedded ranges onto `JsFormatContext` (:579-584). `transform` unconditionally runs the CST→CST syntax_rewriter (`Some(transform(root.clone()))`). Range requests funnel through the generic `format_range` after `is_range_formatting_node` filters eligible roots.
**Invariants:** (1) Empty-ranges means NO delegation: embedded placeholders would dangle unresolved, so the flag is derived, never passed independently — desyncing them leaves StartEmbedded tags unprintable. (2) `is_range_formatting_node` must REJECT statement FRAGMENTS (variable declaration without its statement wrapper) or range edits mis-indent; the explicit blacklist precedes the whitelist. (3) Comments must be built BEFORE context creation because the source map feeds comment-position remapping. (4) transform returning `Option` lets languages opt out of rewriting — JS always opts IN.
**Probe:** `grep -c '!embedded_node_ranges.is_empty()' crates/biome_js_formatter/src/lib.rs` → `1` (:621); `grep -c 'with_embedded_node_ranges' crates/biome_js_formatter/src/lib.rs` → `3` (:535 def, :582 ctx, :624 call); `grep -n 'fn is_range_formatting_node' crates/biome_js_formatter/src/lib.rs` → `553:`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"JsFormatLanguage create_context transform","limit":6,"detail":"ids"}'
```
Resolves `JsFormatLanguage.new 528-533 / .transform 546-551 / .options 569-571 / .create_context 573-585` line-exact.

## Verdict
Adopt the three-trait-type bootstrap shape (SyntaxLanguage/Context/FormatRule) and the emptiness-derived delegation flag; adapt the range whitelist to your grammar's statement kinds. Direct tests: `test_range_formatting*` family (lib.rs tests :681-1110, incl. out-of-bounds error case) pins range behavior through this impl; embedded two-phase pairing is pinned by the html-formatter side capsules (formatter-embedded-two-phase).
