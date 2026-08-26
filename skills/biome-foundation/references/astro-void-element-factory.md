<!-- capsule-v2 -->
# Astro void-element slashless self-closing + optional-slash factory — how does a parser accept HTML-style `<br>` in a JSX dialect, and how must the CST factory change so the slash token becomes OPTIONAL?

**Source:** Biome MIT `main@88f805e19b67ab4c876e4fc4a8b4018bd03df20b`; Codebase Memory project `biome`. **Question:** How do you let `<br>` complete as SELF_CLOSING without consuming `/`, and what breaks downstream when `slash_token` goes Option?

## is_at_astro_void_element gate + OpeningElement::SelfClosing
**Path/Symbol:** `crates/biome_js_parser/src/syntax/jsx/mod.rs:parse_any_jsx_opening_tag` (:188-254; void arm :241-247), `is_at_astro_void_element` (:258-263); vocabulary `VOID_ELEMENTS` (:783) + `is_void_element` (:790-792) in biome_js_syntax/src/jsx_ext.rs; generated builder (biome_js_factory/src/generated/node_factory.rs `jsx_self_closing_element` / `JsxSelfClosingElementBuilder.with_slash_token`).
**Signature:** `fn is_at_astro_void_element(p: &JsParser, name: Option<&CompletedMarker>) -> bool`; `pub fn is_void_element(name: &str) -> bool`.
**Data Shape:** Void elements: 14 lowercase spec names `area base br col embed hr img input link meta param source track wbr` — case-SENSITIVE exact match (`contains(&name)`), so a PascalCase `<Br>` never matches. The lint rule's own list keeps 16 (adds legacy `keygen menuitem`) — two vocabularies on purpose.

### Decisive source
```rust
if p.eat(T![/]) {
    expect_jsx_token(p, T![>], !in_expression);
    Some(OpeningElement::SelfClosing(m.complete(p, JSX_SELF_CLOSING_ELEMENT)))
} else if is_at_astro_void_element(p, name.as_ref()) {
    expect_jsx_token(p, T![>], !in_expression);   // '>' bumps with CHILD context — children may follow
    Some(OpeningElement::SelfClosing(
        m.complete(p, JSX_SELF_CLOSING_ELEMENT),  // completed WITHOUT any slash token
    ))
} else { /* plain opening element */ }

fn is_at_astro_void_element(p: &JsParser, name: Option<&CompletedMarker>) -> bool {
    if !Astro.is_supported(p) || !p.at(T![>]) { return false; }
    name.is_some_and(|name| is_void_element(p.text(name.range(p))))
}
```
```rust
// jsx_ext.rs — the parser-side vocabulary EXCLUDES legacy voids:
/// Deliberately excludes the legacy `keygen` and `menuitem`, which Astro requires
/// a closing tag for.
const VOID_ELEMENTS: [&str; 14] = [/* 14 spec names */];
pub fn is_void_element(name: &str) -> bool { VOID_ELEMENTS.contains(&name) }
```
```rust
// node_factory.rs — slash demoted from positional to optional builder field:
pub fn jsx_self_closing_element(l_angle_token, name, attributes, r_angle_token)
    -> JsxSelfClosingElementBuilder   // NO slash parameter anymore
{ ... slash_token: None ... }
pub fn with_slash_token(mut self, slash_token: SyntaxToken) -> Self { self.slash_token = Some(slash_token); self }
// build(): self.slash_token.map(...)  → slot can be EMPTY (green-tree hole)
```

## Flow
1. After attributes, if no `/` was eaten AND dialect is Astro AND next token is `>` AND the just-parsed name is one of the 14 void names ⇒ complete `JSX_SELF_CLOSING_ELEMENT` directly.
2. The critical lex-context detail: this arm calls `expect_jsx_token(p, T![>], !in_expression)` — same as the SLASH arm, NOT the plain-opening arm. At expression root the `>` bumps with `JsxChild` context so whatever follows re-lexes as child content.
3. Downstream formatter treats it exactly like slashed self-closing (see astro-void-slashless-formatting): `AnyJsxOpeningElement::has_slash()` checks token PRESENCE, not node kind.
4. Factory consumers migrated from 5-positional to 4-positional + `.with_slash_token(...)` in the SAME commit (both analyze fix builders updated); doc-examples in jsx_ext.rs rewritten to match.

## Invariant
- **Slashless ≠ opening element:** the completed kind is still `JSX_SELF_CLOSING_ELEMENT` even though its slash slot is empty — every consumer that pattern-matched "self-closing ⇒ has slash token" had to move to presence-checks (`has_slash()`/`element.slash_token().is_some()`). A port that instead completes `JSX_OPENING_ELEMENT` would demand a closing tag and break the fixture.
- **Two void vocabularies are deliberate:** parser accepts 14 (Astro spec-compliance: legacy keygen/menuitem need closing tags there); the correctness LINT keeps 16 because its rule fires on JSX trees where legacy elements are also void. Copying one list into the other role silently changes both parse and diagnostics behavior.
- Gate order: Astro-dialect check FIRST, then `p.at(T![>])`, then name lookup via marker range text — cheap rejection before string work.

## Probe (direct tests)
From repo root:
- Fixture ok: `cat crates/biome_js_parser/tests/js_test_suite/ok/astro_void_element.astro_expr.tsx` → `cond && <br>` (no error, parses clean).
- Error twin proves the gate is Astro-only: `grep -c 'expected `<' crates/biome_js_parser/tests/js_test_suite/error/jsx_void_element_without_slash.tsx.snap` → ≥1 (`<br>` unclosed in TSX errors).
- Legacy refusal inside Astro: fixture `error/astro_legacy_void_element.astro_expr.tsx.snap` contains `× expected `<` but instead the file ends` for `<keygen>` (keygen NOT auto-self-closed in Astro).
- Vocabulary split: `grep -c 'keygen' crates/biome_js_syntax/src/jsx_ext.rs` → **1** (comment only); `grep -n 'keygen.*menuitem' crates/biome_js_analyze/src/lint/correctness/no_void_elements_with_children.rs` hits the 16-element list (:294-297).
- Builder shape: `grep -c 'with_slash_token' crates/biome_js_factory/src/generated/node_factory.rs crates/biome_js_analyze/src/lint/correctness/no_void_elements_with_children.rs crates/biome_js_analyze/src/lint/style/use_self_closing_elements.rs` → 1 each (definition + two migrated fix builders).

## Retrieve
```
codebase-memory-mcp cli search_graph --project biome --name-pattern 'is_at_astro_void_element|is_void_element'
```
→ `is_at_astro_void_element Function :258-263` (parser), `is_void_element Function jsx_ext.rs :790-792`, plus html-syntax's unrelated `HtmlSelfClosingElement.is_void_element` twin (:249-252) — route by file, not name.

## Verdict
Adopt: optional-token factory slots + presence-based downstream checks are the reusable contract for dialects that relax required syntax; adapt the void list to your target HTML spec vintage. Omit Biome's embedding-kind plumbing if you have a simpler dialect flag.

---
**Erratum (pass-15 drift repair):** supersedes pass-4 `jsx-tag-skeleton`'s two-arm completion ladder (slash vs plain) — at pin `88f805e1` there are THREE arms; `parse_any_jsx_opening_tag` spans :188-254 and the old `SelfClosing(m.complete(...))` excerpt now needs the `is_at_astro_void_element` arm between them.
