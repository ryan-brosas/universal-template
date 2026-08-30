<!-- capsule-v2 -->
# JSX attribute list — how do spread, shorthand, namespace, and value-less attributes coexist, and why is the attribute `=` bumped with a dedicated lex context?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What dispatch order and value grammar make `<div use:validate="a" el=<a/> {...obj} novalue />` parse as one list?

## JsxAttributeList + initializer/value chain
**Path/Symbol:** `crates/biome_js_parser/src/syntax/jsx/mod.rs:JsxAttributeList` (:560-602), `parse_jsx_attribute` (:603-615), `parse_jsx_spread_attribute` (:631-659), `is_at_jsx_shorthand_attribute` (:664-671), `parse_jsx_attribute_initializer_clause` (:686-702), `parse_jsx_attribute_value` (:704-722). *(Ranges re-pinned after the pass-15 Astro insert in this file; dispatch logic unchanged.)*
**Signature:** `impl ParseNodeList for JsxAttributeList` (end at `>` | `/` | `<`; recovery set `{/, >, <, {, }, ..., ident}`).
**Data Shape:** Attribute kinds: `JSX_ATTRIBUTE` (+ optional `JSX_ATTRIBUTE_INITIALIZER_CLAUSE` → string | `{expr}` | nested element), `JSX_SPREAD_ATTRIBUTE`, Astro-only `JSX_SHORTHAND_ATTRIBUTE`.

### Decisive source
```rust
fn parse_element(&mut self, p: &mut JsParser) -> ParsedSyntax {
    if is_at_jsx_shorthand_attribute(p) {        // Astro gate FIRST: { ident }
        parse_jsx_shorthand_attribute(p)
    } else if matches!(p.cur(), T!['{'] | T![...]) {
        parse_jsx_spread_attribute(p)            // {...expr} — comma-sequence rejected
    } else if is_at_metavariable(p) {
        parse_metavariable(p)
    } else {
        parse_jsx_attribute(p)                   // name[/ns][:?] [= value]?
    }
}
```
```rust
// the '=' that starts a value changes lexing for what follows:
p.bump_with_context(T![=], JsLexContext::JsxAttributeValue);
parse_jsx_attribute_value(p).or_add_diagnostic(p, jsx_expected_attribute_value);
// value: '{' expr '}'  |  <nested-tag/>  |  JSX_STRING_LITERAL
```

**Flow:** per element: shorthand (embedding-gated) → spread (`{...}` with sequence-expression rejection) → metavariable → plain attribute with optional initializer. Spread requires BOTH `{` and `...` via expect (so `{obj}` without dots recovers into the spread branch's diagnostics rather than silently parsing an expression container).
**Invariant:** The attribute-value lex context exists because string literals in attributes have different escape/quote rules than JS strings; bumping `=` plainly would mis-tokenize `id="a"`. Nested element values recurse through `parse_any_jsx_tag(p, true)` — attributes are full expression roots. Value-less attributes are legal; the initializer clause is simply Absent.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/jsx_element_attributes.jsx` (`novalue el=<a/>`, dashed namespaced `use-dashed_underscore:validate="ahaha"`) vs `error/jsx_spread_attribute_error.jsx` (`{...obj, other}`, `{obj}`, `<a ...obj}`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "JsxAttributeList spread attribute initializer JsxAttributeValue", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ordered dispatch + context-bumped `=` + three-shape value grammar; adapt embedding-kind gating to host dialects; omit message text.
