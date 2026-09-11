<!-- capsule-v2 -->
# Await/yield contextual keyword reparse — when is `await` an identifier and when an operator?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How do you parse context-sensitive keywords that are only operators in certain scopes, without a second token stream?

## parse_unary_expr await arm + yield gate
**Path/Symbol:** `crates/biome_js_parser/src/syntax/expr.rs:parse_unary_expr` await arm (:1870-1932), `parse_yield_expression` (:420-466), dispatch guard `parse_assignment_expression_or_higher_base` (:300-316); identifier legality `parse_identifier` (:1475-1532).
**Signature:** `fn parse_unary_expr(p: &mut JsParser, context: ExpressionContext) -> ParsedSyntax`
**Data Shape:** Decision inputs: `state.in_async()`, `state.is_top_level() || state.in_function()`, presence of the parsed unary operand, `in_generator()`, ambient-context flag.

### Decisive source
```rust
let is_top_level_module_or_async_fn =
    p.state().in_async() && (p.state().is_top_level() || p.state().in_function());

if !is_top_level_module_or_async_fn {
    if unary.is_absent() {
        p.rewind(checkpoint);       // `await;` / `await` as bare identifier
        m.abandon(p);
        return parse_identifier_expression(p);
    }
    // operand present but context illegal -> keep the tree shape, mark it bogus
    p.error(/* "`await` is only allowed within async functions..." */);
    let expr = m.complete(p, JS_BOGUS_EXPRESSION);
    return Present(expr);
}
```

**Flow:** at `await`: speculatively parse the operand first → legal async context: complete as `JS_AWAIT_EXPRESSION` (missing operand = diagnostic) → illegal context with NO operand: rewind checkpoint, abandon marker, reparse as identifier expression → illegal context WITH operand: keep the await-node shape but complete as bogus + error. Yield mirrors this at the assignment level: only treated as an operator when `in_generator() || nth(1) starts an expression`, else falls through to ordinary expression parsing.
**Invariant:** The *shape* of the output tree depends on whether an operand followed — a missing operand in sloppy script must produce a plain identifier node, not an empty/bogus await. Ambient contexts (`declare`) suppress the await-as-identifier error entirely (:1502-1518). These decisions use parser state flags, never lexer modes.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/js/reparse_await_as_identifier.js` + `reparse_yield_as_identifier.js` (SCRIPT-tagged corpora) and `error/no_top_level_await_in_scripts.js`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_unary_expr await reparse identifier", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt speculative-operand-then-classify for contextual keywords; adapt the scope predicates to your language's reserved-word rules; omit module/top-level-await special cases where N/A.
