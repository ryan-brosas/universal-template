<!-- capsule-v2 -->
# Stack-based precedence climbing — how do you parse binary expressions iteratively with correct left associativity?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does an explicit stack replace recursion for binary/logical expression parsing while keeping precedence and associativity exact?

## parse_binary_or_logical_expression
**Path/Symbol:** `crates/biome_js_parser/src/syntax/expr.rs:parse_binary_or_logical_expression` (:531-695).
**Signature:** `fn parse_binary_or_logical_expression(p: &mut JsParser, left_precedence: OperatorPrecedence, context: ExpressionContext) -> ParsedSyntax`
**Data Shape:** Stack of `(OperatorPrecedence, Option<(JsSyntaxKind /*node kind*/, Marker)>)`; operators come from `p.re_lex(JsReLexContext::BinaryOperator)` (the current token is re-lexed in operator context — `/` becomes a division only here).

### Decisive source
```rust
let stop_at_current_operator = if new_precedence.is_right_to_left() {
    new_precedence < left_precedence     // right-assoc: stop on strictly-lower
} else {
    new_precedence <= left_precedence    // left-assoc: stop on lower-or-equal
};
if stop_at_current_operator { break; }
// ...
stack.push((left_precedence, Some((expression_kind, m))));
left_precedence = new_precedence;
left = parse_unary_expr(p, context).or_else(|| parse_private_name(p));
```

**Flow:** seed stack with `(caller precedence, None)` → inner loop eats every operator binding tighter than `left_precedence`, pushing `(old_prec, marker)` frames → when a lower/equal operator appears, pop the stack: each frame completes its marker around the accumulated RHS (`m.complete(p, kind)`) so outer operators close after inner ones → recursion depth bounded by `count(OperatorPrecedence)` because the inner loop immediately returns when the next operator doesn't bind tighter.
**Invariant:** Associativity is encoded *only* in the `<` vs `<=` comparison — flipping either arm swaps associativity globally. `**` additionally rejects unparenthesized unary LHS with a diagnostic + `JS_BOGUS_EXPRESSION` (:597-607), and `as`/`satisfies`/`in` are gated by line-break and `ExpressionContext::INCLUDE_IN` before they count as binary operators at all (:556-561).
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/exponent_unary_unparenthesized.js` (`-a ** b` must error) plus snapshot corpus for mixed `a || b && c ?? d` chains.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_binary_or_logical_expression OperatorPrecedence stack", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the explicit-stack precedence climber whenever your parser language already has deep expression nesting; adapt precedence/associativity tables and re-lex gating; omit Biome's TS-specific `as`/`satisfies` arms in non-TS hosts.
