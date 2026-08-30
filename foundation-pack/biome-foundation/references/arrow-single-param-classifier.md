<!-- capsule-v2 -->
# Single-parameter arrow + async-identifier split — when is `async x => …` an arrow and when is `async` just a call callee, decided with at most three tokens?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does the parser classify unparenthesized arrow heads (`a =>`, `async a =>`) against identifier expressions without speculation or rewind?

## is_arrow_function_with_single_parameter
**Path/Symbol:** `crates/biome_js_parser/src/syntax/function.rs:parse_arrow_function_with_single_parameter` (:857-886), predicate `is_arrow_function_with_single_parameter` (:888-903), dispatch from `parse_arrow_function_expression` (:527-533).
**Signature:** `fn is_arrow_function_with_single_parameter(p: &mut JsParser) -> bool` — pure `p.nth_at(n)` probe.
**Data Shape:** Dispatch order matters: parenthesized path runs first (`parse_parenthesized_arrow_function_expression.or_else(single_parameter)`); the single-param path only ever sees non-`(` heads.

### Decisive source
```rust
// a => ...
if p.nth_at(1, T![=>]) {
    // let id = async => async;   ← 'async' is the parameter, NOT a modifier
    is_at_identifier_binding(p) && !p.has_nth_preceding_line_break(1)
}
// async ident => ...
else {
    p.at(T![async])
        && !p.has_nth_preceding_line_break(1)
        && is_nth_at_identifier_binding(p, 1)
        && !p.has_nth_preceding_line_break(2)
        && p.nth_at(2, T![=>])
}
```
And inside the parse: `let is_async = p.at(T![async]) && is_nth_at_identifier_binding(p, 1);` — the modifier is eaten **only** if an identifier binding follows; otherwise `async` itself binds as the parameter name (`async => async`).
**Flow:** `ident =>` (no line break before `=>`) ⇒ single-param arrow; `async` + line break ⇒ not a modifier; `async ident =>` (no breaks anywhere in the triple) ⇒ async single-param arrow. Parameters parse under `EnterParameters(arrow_function_parameter_flags(p, flags))` — arrows inherit parent async/generator context for `yield`/`await` legality (see capsule on signature-flags threading).
**Invariant:** Line-break checks are part of legality (`async \n x =>` is `async(x)` call syntax territory); `is_at_identifier_binding` (not raw-identifier) enforces `await`/`yield` contextual rules per mode. The `async`-as-parameter case means "eat `async`" must be *conditional*, unlike every other arrow head where it's a plain eat.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/arrow_expr_single_param.cjs` (`foo => {}`, `yield => {}`, `await => {}`, `baz =>\n{}`) and `ok/async_arrow_expr.js` / error variant pinning `async await => {}` rejection.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "is_arrow_function_with_single_parameter async identifier binding", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bounded-probe classification (≤3 tokens, zero allocation, no checkpoint); adapt to host token API; omit Biome-specific binding predicates' internals (owned by `binding-legality-gate.md`). Completes the arrow trilogy: classifier → speculation protocol → this cheap path.
