<!-- capsule-v2 -->
# FormatNodeRule template method — where do suppression, comments, parens spacing and embedded delegation hook into per-node formatting?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** A porter bootstrapping a language formatter must reproduce the EXACT default pipeline a node goes through before its `fmt_fields` runs — which steps are ordered and which are overridable?

## The fmt() ladder in biome_js_formatter/src/lib.rs
**Path/Symbol:** `crates/biome_js_formatter/src/lib.rs:358-371` (`FormatNodeRule::fmt`), `lib.rs:374-410` (`fmt_node` paren+embedded handling), `lib.rs:431-458` (comment hooks), `lib.rs:481-492` (`FormatJsSyntaxToken` tracks every token). *(Ranges +1 after pass-15's `mod astro;` insert; template unchanged.)*
**Signature:** `fn fmt(&self, node: &N, f: &mut JsFormatter) -> FormatResult<()>` on `trait FormatNodeRule<N> where N: AstNode<Language = JsLanguage> + Debug`; extension point `fn fmt_fields(&self, item: &N, f: &mut JsFormatter) -> FormatResult<()>`.
**Data Shape:** pipeline stages as trait methods with defaults: `is_suppressed`/`is_global_suppressed` → comment hooks (`fmt_leading_comments`, `fmt_dangling_comments`, `fmt_trailing_comments`) → `fmt_node` → `fmt_fields` + optional hooks `needs_parentheses()`, `embedded_node_range()`.

### Decisive source
```rust
// lib.rs:361-370 — the ordered template method
fn fmt(&self, node: &N, f: &mut JsFormatter) -> FormatResult<()> {
    if self.is_suppressed(node, f) || self.is_global_suppressed(node, f) {
        return write!(f, [format_suppressed_node(node.syntax())]);
    }
    self.fmt_leading_comments(node, f)?;
    self.fmt_node(node, f)?;
    self.fmt_dangling_comments(node, f)?;
    self.fmt_trailing_comments(node, f)
}
// lib.rs:385-398 — embedded delegation INSIDE fmt_node, between parens writes
if let Some(range) = self.embedded_node_range(node, f) {
    let state = f.state_mut();
    for token in node.syntax().tokens() { state.track_token(&token); }  // coverage across phases!
    f.write_elements(vec![
        FormatElement::Tag(StartEmbedded(range)),
        FormatElement::Tag(EndEmbedded),
    ])?;
} else {
    self.fmt_fields(node, f)?;
}
```

**Flow:** suppression check short-circuits to verbatim printing → leading comments → `fmt_node`: opening paren (if `needs_parentheses`, honoring `f.options().delimiter_spacing()` for `( (` vs `(`), then EITHER the two-tag embedded placeholder OR `fmt_fields`, then closing paren with same spacing rule → dangling comments → trailing comments. Every token visited through `FormatJsSyntaxToken` calls `f.state_mut().track_token(token)` (:484) so the debug "all tokens printed" audit stays total.
**Invariants:** (1) Suppression beats everything — a suppressed node must not run fmt_fields at all. (2) Embedded nodes STILL get their tokens pre-tracked before emitting the placeholder pair, otherwise pass-1 debug coverage fails when phase-2 formats the range later. (3) Dangling-comments DEFAULT sits at end-of-node ("isn't ideal but ensures no comments are dropped", :442) — overriding rules must re-add it manually if they custom-format children. (4) Paren spacing is an option-driven symmetric write around the delegated content.
**Probe:** `grep -c 'track_token' crates/biome_js_formatter/src/lib.rs` → `2` (token rule `f.state_mut().track_token(token)` :484 DIRECTLY; embedded loop :390 through the LOCAL binding `state.track_token(&token)` after `let state = f.state_mut()` :388 — the two spellings differ, do not count them with one pattern); `grep -n 'fn fmt_fields' crates/biome_js_formatter/src/lib.rs` → `412:`; `grep -c 'JS_VARIABLE_DECLARATION' crates/biome_js_formatter/src/lib.rs` → `1`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"FormatNodeRule fmt_fields needs_parentheses","limit":8,"detail":"ids"}'
```
Resolves the trait's Method cluster line-exact; generated rule impls live under `crates/biome_js_formatter/src/{js,ts,jsx}/` and are indexed per file.

## Verdict
Adopt the ordered template-method ladder and the four override points; adapt trait names. This capsule pairs with formatter-orphan-rule-bridge (generic blanket impls) — together they are the full "port a language formatter" bootstrap. Direct tests: snapshot suites per node kind exercise the ladder; `format_range` tests pin the paren/embedded arms indirectly.
