<!-- capsule-v2 -->
# Implicit-fragment child comment rescue + slashless self-closing printing — how does a formatter print delimiter-less sibling tags without eating their comments or inventing `<>` delimiters?

**Source:** Biome MIT `main@88f805e19b67ab4c876e4fc4a8b4018bd03df20b`; Codebase Memory project `biome`. **Question:** JSX children are comment-free by construction (comments live on the surrounding fragment), so what happens to comments when the "fragment" is an invisible AST node with real children — and where must the printer stop emitting spaces it used to guarantee?

## is_implicit_fragment_child probe + three-hook override
**Path/Symbol:** `crates/biome_js_formatter/src/utils/jsx.rs:is_implicit_fragment_child` (:586-590); consumers overriding comment hooks: `jsx/tag/element.rs` (fmt_leading/dangling/trailing :23-26/:35-38/:46-49), `jsx/tag/fragment.rs` (:21-24/:33-36/:46-50), `jsx/tag/self_closing_element.rs` (:25-28/:39-42/:54-57); new rule module `astro/auxiliary/implicit_fragment.rs` (`FormatAstroImplicitFragment` = pure `children.format()`); AnyJsxTag dispatch arm (`jsx/any/tag.rs`).
**Signature:** `pub(crate) fn is_implicit_fragment_child(node: &JsSyntaxNode) -> bool`.
**Data Shape:** Probe walks TWO levels up: node → parent list → grandparent, and checks `AstroImplicitFragment::can_cast(grandparent.kind())`. The double-hop is required because children always sit inside a `JSX_CHILD_LIST` wrapper node under the fragment.

### Decisive source
```rust
// utils/jsx.rs
/// Children of a delimiter-less fragment carry real comments, unlike JSX children.
pub(crate) fn is_implicit_fragment_child(node: &JsSyntaxNode) -> bool {
    node.parent()
        .and_then(|list| list.parent())
        .is_some_and(|parent| AstroImplicitFragment::can_cast(parent.kind()))
}

// jsx/tag/element.rs (same pattern ×3 hooks in element/fragment/self_closing):
fn fmt_leading_comments(&self, node: &JsxElement, f: &mut JsFormatter) -> FormatResult<()> {
    if is_implicit_fragment_child(node.syntax()) {
        return format_leading_comments(node.syntax()).fmt(f);  // REAL printing ladder
    }
    debug_assert!(
        !f.comments().has_leading_comments(node.syntax()),
        "JsxElement can not have comments."
    );
    Ok(())
}
```
```rust
// astro/auxiliary/implicit_fragment.rs — the WHOLE new rule:
impl FormatNodeRule<AstroImplicitFragment> for FormatAstroImplicitFragment {
    fn fmt_fields(&self, node: &AstroImplicitFragment, f: &mut JsFormatter) -> FormatResult<()> {
        let AstroImplicitFragmentFields { children } = node.as_fields();
        write!(f, [children.format()])   // NO delimiters, NO separators — just the child stream
    }
}
```
```rust
// opening_element.rs — spacing flips from "always" to "only when a slash exists":
-                        space(),
+                        self.has_slash().then(space),
...
-                    if self.is_self_closing() {
+                    if self.has_slash() {
...
+    /// Astro `<br>` is self-closing without a slash: emit no space before `>`.
+    fn has_slash(&self) -> bool {
+        match self {
+            Self::JsxSelfClosingElement(element) => element.slash_token().is_some(),
+            Self::JsxOpeningElement(_) => false,
+        }
+    }
```

## Flow
1. `FormatAnyJsxTag` gains the `AstroImplicitFragment` dispatch arm; its rule prints only the child list — delimiter-less by construction.
2. Every child-formatting rule that carried a debug_assert "children can't have comments" now FIRST probes `is_implicit_fragment_child`; true ⇒ delegate to the standard comment ladders instead of asserting emptiness.
3. Fragment-in-fragment nesting: a real `<>…</>` inside an implicit one IS a child of the implicit fragment, so `JsxFragment` needs the same rescue (in-source comment documents exactly this).
4. Suppression interplay stays intact: `is_jsx_suppressed` matches `{/*comment*/}` empty-expression-child siblings — works unchanged for implicit-fragment children since their JsxChildList shape is identical.
5. Void elements printed via `AnyJsxOpeningElement`: `has_slash()` presence-check replaces kind-check in three spots so `<br>` prints WITHOUT a trailing space and never gets a synthesized `/`.

## Invariant
- **Debug-asserts are contracts, not decoration:** rather than weakening "JsxElement can not have comments", upstream added a narrow predicate escape hatch that routes to the real printing machinery. Porting this as "delete the asserts" would silently DROP comments; porting as "always run the ladders" would break suppression semantics elsewhere. The predicate-scoped delegation IS the pattern.
- **Spacing follows token presence, not node class:** after making slash optional, `is_self_closing()` (kind-based) and `has_slash()` (token-presence) diverge exactly for Astro voids. Any layout decision keyed on the old predicate prints `<br >` or synthesizes `/`.
- The formatter NEVER adds `<>` delimiters around implicit fragments (test pins absence) but MUST keep them for explicit fragments (twin test).

## Probe (direct tests)
From repo root (biome_js_formatter/src/lib.rs tests):
- `grep -cE 'fn format_.*implicit_fragment|fn format_keeps_explicit' crates/biome_js_formatter/src/lib.rs` → **4** (keeps_comment_between_implicit_fragment_siblings / keeps_comment_before_an_implicit_fragment_element / does_not_add_delimiters_to_an_implicit_fragment / keeps_explicit_fragment_delimiters). The FIFTH test's name matches neither alternation branch — pin it separately: `grep -c 'fn format_keeps_comment_before_a_nested_explicit_fragment' crates/biome_js_formatter/src/lib.rs` → **1** (nested explicit fragment inside an implicit one still carries comments).
- Harness: `grep -c 'with_embedding_kind' crates/biome_js_formatter/src/lib.rs` → **1** (`format_astro_template` builds `tsx().with_embedding_kind(JsEmbeddingKind::Astro { frontmatter: false, is_class_attribute: false })`).
- Comment-position assertions pin ORDER, not just presence: `output.find("/* c */") > find("<p>") && < find("<div />")` — hoisting/sinking both fail the test.
- Consumer census: `grep -rc 'is_implicit_fragment_child' crates/biome_js_formatter/src/jsx/tag/element.rs crates/biome_js_formatter/src/jsx/tag/fragment.rs crates/biome_js_formatter/src/jsx/tag/self_closing_element.rs` → **4 each** (import + 3 hooks); `grep -c 'has_slash' crates/biome_js_formatter/src/jsx/tag/opening_element.rs` → **4** (:47, :53, :89 use sites + :153 def).
- React-compiler boundary: `grep -c 'AstroImplicitFragment' crates/biome_react_compiler/src/convert_ast/jsx.rs` → **2**, each arm `Err(unsupported(fragment.syntax()))` with comment "Astro syntax; React never sees it".

## Retrieve
```
codebase-memory-mcp cli search_graph --project biome --name-pattern 'is_implicit_fragment_child|FormatAstroImplicitFragment'
```
→ `is_implicit_fragment_child Function utils/jsx.rs :586-590`, `FormatAstroImplicitFragment Struct astro/auxiliary/implicit_fragment.rs :5-5` (line-exact at pin).

## Verdict
Adopt: predicate-scoped comment-hook rescue is the reusable contract for ANY invisible grouping node introduced into a comment-free region (template dialects, macro expansions, synthetic wrappers). Adapt `has_slash` presence-checking to any optional-token you introduce; omit the React-compiler rejection arms unless you have a cross-dialect consumer.

---
**Erratum (pass-15 drift repair):** pass-12's `js-formatter-node-rule-template` cites biome_js_formatter/src/lib.rs:357-370/373-409/430-457/480-491 — those ranges shift +1 line at this pin (`mod astro;` inserted at :168); template content unchanged. `js-formatter-language-integration` :519-586/:599-651 likewise +1 (now struct at :521, format_range :600, format_node :617, format_sub_tree :650).
