<!-- capsule-v2 -->
# Arrow-vs-parenthesized disambiguation — how do you decide `(a, b)` is a parenthesized expression or arrow parameters without unbounded lookahead?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What is the full ladder that classifies `(…)`/`<…>`/`async` prefixes into True/False/Unknown before committing to an arrow parse?

## IsParenthesizedArrowFunctionExpression classifier
**Path/Symbol:** `crates/biome_js_parser/src/syntax/function.rs:is_parenthesized_arrow_function_expression` (:690-716) and `_impl` (:719-831).
**Signature:** `fn is_parenthesized_arrow_function_expression(p: &mut JsParser) -> IsParenthesizedArrowFunctionExpression` — enum `{True, False, Unknown}`.
**Data Shape:** Pure token-kinds probe over `p.nth(n)` offsets; no events, no errors, no token consumption. `n = usize::from(flags.contains(ASYNC))` skips the consumed `async`.

### Decisive source
```rust
// '()' is an arrow expression if followed by an '=>', a type annotation or body.
// Otherwise, a parenthesized expression with a missing inner expression
match p.nth(n + 2) {
    T![=>] | T![:] | T!['{'] => IsParenthesizedArrowFunctionExpression::True,
    _ => IsParenthesizedArrowFunctionExpression::False,
}
// Rest parameter '(...a' is certainly not a parenthesized expression
T![...] => IsParenthesizedArrowFunctionExpression::True,
// '([ ...', '({ ... } can either be a parenthesized object or array expression or a destructing parameter
T!['['] | T!['{'] => IsParenthesizedArrowFunctionExpression::Unknown,
// '(a, ': separator to next parameter or a parenthesized sequence expression
T![=] | T![,] | T![')'] => IsParenthesizedArrowFunctionExpression::Unknown,
```

**Flow:** `cur ∈ {'(', '<', async}` → classify → `True`: parse head with `Ambiguity::Allowed` (never fails; missing `=>` becomes an error inside); `False`: caller falls through to parenthesized-expression parsing; `Unknown`: `parse_possible_parenthesized_arrow_function_expression` wraps `try_parse_parenthesized_arrow_function_head(Ambiguity::Disallowed)` in `try_parse`, which rewinds on `Err`. JSX adds a parallel `<`-ladder (`<A extends=` → False, `<A extends B>` → Unknown, `<A=`/`<A,` → True).
**Invariant:** Only the *Unknown* branch may rewind-and-fall-back. The classifier must return False (not Unknown) for anything provably not an arrow, otherwise valid code like `(a + b) => {}` would be speculatively re-parsed and its diagnostics duplicated. Failure of the Disallowed head records the start position in `state.not_parenthesized_arrow` so the same position never speculates twice.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/paren_or_arrow_expr.js` (both readings parse) + `error/paren_or_arrow_expr_invalid_params.js` (`(5 + 5) => {}` errors once, as an arrow with invalid params).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "is_parenthesized_arrow_function_expression Unknown try_parse", limit: 10, fields: ["signature", "name", "file"] });
```
Resolves `syntax.function.is_parenthesized_arrow_function_expression` (:690-716).

## Verdict
Adopt the three-way classifier + memoized negative speculation as the canonical ambiguous-prefix pattern; adapt the token ladders to your grammar's ambiguities; omit the JS-specific JSX branch when porting to another language.
