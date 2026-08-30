<!-- capsule-v2 -->
# JSX expression-child whitelist — why is `{class A{}}` rejected but `{function f(){}}` accepted, and how does `{...a}` as a CHILD differ from a spread attribute?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What exact kind blacklist (and sequence-expression special case) governs JSX container expressions, and where does the closing `}` recover?

## parse_jsx_expression_child + parse_jsx_assignment_expression
**Path/Symbol:** `crates/biome_js_parser/src/syntax/jsx/mod.rs:parse_jsx_expression_child` (:436-476), `parse_jsx_assignment_expression` (:808-836), skipped-trivia recovery in `parse_jsx_expression_attribute_value` (:725-741). *(Ranges re-pinned after the pass-15 Astro insert; whitelist unchanged.)*
**Signature:** `fn parse_jsx_assignment_expression(p: &mut JsParser, is_spread: bool) -> ParsedSyntax` — parses full `parse_expression`, then post-filters kinds.
**Data Shape:** Child kinds: `JSX_EXPRESSION_CHILD` / `JSX_SPREAD_CHILD` (`{...a}` — legal in children, unlike attributes' comma ban which also applies here via shared filter). Rejected kinds: `JS_IMPORT_META_EXPRESSION`, `JS_NEW_TARGET_EXPRESSION`, `JS_CLASS_EXPRESSION`; plus `JS_SEQUENCE_EXPRESSION` when spread.

### Decisive source
```rust
let err = match expr.kind(p) {
    JS_IMPORT_META_EXPRESSION | JS_NEW_TARGET_EXPRESSION | JS_CLASS_EXPRESSION => Some(…),
    JS_SEQUENCE_EXPRESSION if is_spread => Some(…),
    _ => None,
};
if let Some(err) = err { p.error(err); expr.change_to_bogus(p); }
```
Missing-`}` recovery in children:
```rust
expect_jsx_token(p, T!['}'], true);
// …and the attribute-value variant's salvage for doubled braces:
if !p.expect(T!['}']) && p.nth_at(1, T!['}']) {
    p.parse_as_skipped_trivia_tokens(|p| { p.bump_any(); });
    p.expect(T!['}']);
}
```

**Flow:** `{` → optional `...` (spread child; requires an expression) → full expression parse → kind-filter with bogus demotion → `}` bumped with child context. Function expressions pass; class expressions, `import.meta`, and `new.target` fail — matching React/TS runtime semantics, not grammar.
**Invariant:** The filter runs on COMPLETED markers (`change_to_bogus`) — parse first, validate by kind second; never pre-gate on start tokens or you lose recovery quality. The spread flag only *adds* the sequence-expression rejection; base rejections are identical for children and attribute values. Doubled-brace salvage keeps one brace as trivia instead of cascading errors.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/jsx_children_expression.jsx` (40+ accepted forms incl. `{yield a}`, `{import("a.js")}`) vs `error/jsx_children_expressions_not_accepted.jsx` (`{import.meta}`, `{class A{}}`, `{super()}`, `{new.target}`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "jsx assignment expression class expression change_to_bogus spread child", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt completed-node kind filtering over speculative gating; adapt the blacklist to host semantics; omit message text.
