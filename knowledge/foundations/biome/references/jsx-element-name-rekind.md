<!-- capsule-v2 -->
# JSX element-name rekind — how does `<div>` become an intrinsic JSX_NAME while `<Foo.Bar>` becomes a member reference, decided by one lowercase check and post-hoc `change_kind`?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does the parser classify intrinsic vs component vs namespaced vs member element names, and when does a namespace name become bogus?

## parse_jsx_any_element_name + is_intrinsic_element
**Path/Symbol:** `crates/biome_js_parser/src/syntax/jsx/mod.rs:parse_jsx_any_element_name` (:488-510), `is_intrinsic_element` (:519-525), `parse_jsx_name_or_namespace` (:533-544), `parse_jsx_name` (:546-558). *(Ranges re-pinned after the pass-15 Astro insert; rekind logic unchanged.)*
**Signature:** `fn parse_jsx_any_element_name(p: &mut JsParser) -> ParsedSyntax`; `fn is_intrinsic_element(element_name: &str) -> bool` = first char lowercase (React semantics).
**Data Shape:** Kinds: `JSX_NAME` (intrinsic) / `JSX_REFERENCE_IDENTIFIER` (component root) / `JSX_NAMESPACE_NAME` (`ns:name`) / `JSX_MEMBER_NAME` chain (`a.b.c`). Names come from re-lexing via `JsReLexContext::JsxIdentifier` → `JSX_IDENT` (accepts dashes, keywords like `<if />`).

### Decisive source
```rust
name.map(|mut name| {
    if name.kind(p) == JSX_NAME && (p.at(T![.]) || !is_intrinsic_element(name.text(p))) {
        name.change_kind(p, JSX_REFERENCE_IDENTIFIER)   // <div> stays intrinsic; <div.x> or <Div> → reference
    } else if name.kind(p) == JSX_NAMESPACE_NAME && p.at(T![.]) {
        // "JSX property access expressions cannot include JSX namespace names."
        name.change_to_bogus(p);                        // <ns:a.b> — error but keep parsing member chain
    }
    while p.at(T![.]) {
        let m = name.precede(p);
        p.bump(T![.]);
        parse_name(p).or_add_diagnostic(p, expected_identifier);
        name = m.complete(p, JSX_MEMBER_NAME)
    }
    name
})
```

**Flow:** re-lex identifier in JSX context → parse optional `ns:name` → post-hoc classification: plain-lowercase stays intrinsic; dotted or uppercase roots are demoted/promoted to references; namespace+dot errors to bogus yet still builds the `JSX_MEMBER_NAME` chain on top.
**Invariant:** Classification happens AFTER completion via kind changes — the name grammar itself never backtracks. The intrinsic test is text-based (first char), so `<if />`, `<a-b-c />` are intrinsic while `<Object />` is a component; this must match React's resolution rules or downstream tooling mis-binds components. Namespace names may not participate in member access but the member loop runs regardless — structure survives the error.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/jsx_member_element_name.jsx` (`<a.b.c.d>`, `<a-b.c>`, `<Abcd>`) and `ok/jsx_any_name.jsx` (`<if />`, `<dashed-namespaced:dashed-name />`) vs `error/jsx_namespace_member_element_name.jsx`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_jsx_any_element_name intrinsic change_kind namespace", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt parse-then-rekind with first-char intrinsic rule; adapt to host's JSX dialect flags; omit nothing portable. Fourth instance of Biome's change_kind pattern.
