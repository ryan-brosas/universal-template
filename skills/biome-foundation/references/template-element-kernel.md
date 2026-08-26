<!-- capsule-v2 -->
# Template-element kernel — how does ONE loop parse both expression templates and type templates with lexer-context-correct re-entry?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How do I port template-literal parsing so `${…}` substitutions work identically for JS expressions and TS types without duplicating the state machine?

## parse_template_elements
**Path/Symbol:** `crates/biome_js_parser/src/syntax/expr.rs:parse_template_elements` (:1606-1656); callers `parse_ts_template_literal_type` (`crates/biome_js_parser/src/syntax/typescript/types.rs:1618-1637`, kinds TS_TEMPLATE_CHUNK_ELEMENT/TS_TEMPLATE_ELEMENT, tagged=false) and the JS template-literal path in expr.rs (JS kinds, tagged per tag presence).
**Signature:** `fn parse_template_elements<P>(p, chunk_kind, element_kind, tagged: bool, parse_element: P) where P: Fn(&mut JsParser) -> Option<CompletedMarker>` — caller owns the wrapper marker + element list node.
**Data Shape:** Lexer pre-splits the raw text into TEMPLATE_CHUNK / DOLLAR_CURLY tokens using `JsLexContext::TemplateElement { tagged }`; the loop sees ONLY those three kinds (plus ERROR_TOKEN) until BACKTICK or EOF.

### Decisive source
```rust
DOLLAR_CURLY => {
    let e = p.start();
    p.bump(DOLLAR_CURLY);
    parse_element(p);
    if !p.at(T!['}']) {
        p.error(expected_token(T!['}']));
        // Seems there's more. For example a `${a a}`. We must eat all tokens away to avoid a panic…
        let _ = ParseRecoveryTokenSet::new(JS_BOGUS,
            token_set![T!['}'], TEMPLATE_CHUNK, DOLLAR_CURLY, ERROR_TOKEN, BACKTICK]).recover(p);
        if !p.at(T!['}']) {
            e.complete(p, element_kind);
            break;                       // failed recovery: exit BEFORE double-completing
        }
    }
    p.bump_with_context(T!['}'], JsLexContext::TemplateElement { tagged });
    e.complete(p, element_kind);
}
ERROR_TOKEN => {
    let err = p.err_builder("Invalid template literal", p.cur_range());
    p.error(err);
    p.bump_with_context(p.cur(), JsLexContext::TemplateElement { tagged });
}
```
Type-side entry (identical kernel, different kinds):
```rust
p.bump_with_context(BACKTICK, JsLexContext::TemplateElement { tagged: false });
let elements = p.start();
parse_template_elements(p, TS_TEMPLATE_CHUNK_ELEMENT, TS_TEMPLATE_ELEMENT, false,
    |p| parse_ts_type(p, context).or_add_diagnostic(p, expected_ts_type));
elements.complete(p, TS_TEMPLATE_ELEMENT_LIST);
p.expect(BACKTICK);
Present(m.complete(p, TS_TEMPLATE_LITERAL_TYPE))
```

**Flow:** open backtick bumped WITH TemplateElement lex-context → loop chunks/substitution-openers → inside `${`, the CLOSURE decides what's allowed (expression grammar vs `parse_ts_type`) → close `}` bumped again with TemplateElement context (re-entering chunk lexing) → final BACKTICK expected by the caller.
**Invariant:** Every bump inside a template MUST carry `JsLexContext::TemplateElement { tagged }` or the lexer mis-tokenizes the following chunk (regex-vs-divide class errors). The recovery set includes TEMPLATE_CHUNK/DOLLAR_CURLY/BACKTICK themselves — recovery may consume template machinery; the `break` after failed recovery prevents completing element `e` TWICE (double-complete panics in rowan). The unreachable arm documents the lexer contract: anything not chunk/$-{/error is a LEXER bug, not a parser one. Literal-type side reuses this verbatim — only kinds + element closure differ; porters who fork the two loops drift on error behavior.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/ts_template_literal_error.ts` (`type C = \`${A B}bcd\``, `type D = \`${A B\``) vs `…/ok/ts_template_literal_type.ts` (`type B = \`a${A}\``).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_template_elements TemplateElement DOLLAR_CURLY", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single parameterized kernel with closure-injected substitution grammar; adapt token names to your lexer; omit the tagged flag only if your language has no tagged templates.
