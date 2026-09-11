<!-- capsule-v2 -->
# JSX tag skeleton + lex-context switching — how do opening/self-closing/closing tags and children share one recursive structure while the lexer switches between code, attribute-value, and child contexts?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What is the canonical shape of JSX element parsing (tag kinds → children → closing-tag matching), and where exactly must lexing context change?

## parse_any_jsx_tag / parse_any_jsx_opening_tag
**Path/Symbol:** `crates/biome_js_parser/src/syntax/jsx/mod.rs:parse_jsx_tag_expression` (:53-79 — pass-15 erratum: now ends with the Astro checkpoint/abandon/rewind speculative tail, see `astro-implicit-fragment-reparse`; the excerpt below is the unchanged core), `parse_any_jsx_tag` (:156-177), `parse_any_jsx_opening_tag` (:188-254), `expect_jsx_token` (:364-374).
**Signature:** `fn parse_any_jsx_tag(p: &mut JsParser, in_expression: bool) -> ParsedSyntax` — `in_expression` true only at the expression root; enum `OpeningElement::{Fragment(CompletedMarker), Element{name, opening}, SelfClosing(CompletedMarker)}`.
**Data Shape:** Entry gate: `<` followed by `>` | identifier-or-keyword | metavariable — anything else stays a comparison. TSX adds optional type arguments after the name.

### Decisive source
```rust
if p.eat(T![/]) {
    expect_jsx_token(p, T![>], !in_expression);   // self-closing: '>' may be followed by child content? NO — not in expression
    Some(OpeningElement::SelfClosing(m.complete(p, JSX_SELF_CLOSING_ELEMENT)))
} else {
    expect_jsx_token(p, T![>], true);             // opening: always before child content
    Some(OpeningElement::Element { opening: m.complete(p, JSX_OPENING_ELEMENT), name })
}
```
```rust
fn expect_jsx_token(p: &mut JsParser, token: JsSyntaxKind, before_child_content: bool) {
    if !before_child_content {
        p.expect(token);
    } else if p.at(token) {
        p.bump_with_context(token, JsLexContext::JsxChild);   // next chars are CHILDREN now
    } else {
        p.error(expected_token(token));
        p.re_lex(JsReLexContext::JsxChild);                   // salvage: current token re-lexed as child text
    }
}
```

**Flow:** `<` → fragment (`<>`) or named opening (name → TSX type args → attribute list → `/`-fork) → for elements: precede opening into element marker → `parse_jsx_children` (`JSX_CHILD_LIST`: nested tags, `{expr}` children, text literals) → closing tag with name-text comparison → complete. The `in_expression` flag controls whether the final `>` bumps with child context (children follow) or plain-expects (end of expression).
**Invariant:** Every token that abuts child content MUST be consumed via `bump_with_context(JsxChild)` or the lexer mis-tokenizes what follows (`</div>some text`). On a missing `>` the recovery path *re-lexes the current token as a child* instead of dropping it — that is why `<a test</a>` degrades gracefully. Closing-tag mismatch is diagnosed by TEXT equality of name markers (`name.text(p)`), not kind.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/jsx_element_open_close.jsx`, `ok/jsx_fragments.jsx` vs `error/jsx_closing_element_mismatch.jsx` (`<test></text>;`, `<some><nested></some></nested>;`) and `error/jsx_closing_missing_r_angle.jsx`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_any_jsx_opening_tag JsxChild bump_with_context closing element", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-kind opening enum + text-matched closing + context-switched boundary tokens; adapt lex-context API to host lexer; omit Biome diagnostics. Root capsule of the JSX plane.
