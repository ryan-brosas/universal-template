<!-- capsule-v2 -->
# ExpressionContext bitflags — which expression ambiguities are resolved by caller context instead of lookahead?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does the parser thread `[+In]`-style spec parameters and `{`-legality down through every recursive expression call?

## ExpressionContext
**Path/Symbol:** `crates/biome_js_parser/src/syntax/expr.rs:ExpressionContext` (:45-176).
**Signature:** `struct ExpressionContext(ExpressionContextFlags)` with builder methods `and_include_in(bool)`, `and_object_expression_allowed(bool)`, `and_in_decorator(bool)`, `and_ts_type_assertion_allowed(bool)`, `and_in_conditional_consequent(bool)`.
**Data Shape:** u8 bitflags: `IncludeIn | AllowObjectExpression | InDecorator | AllowTSTypeAssertion | InConditionalConsequent`. `Default` = INCLUDE_IN | ALLOW_OBJECT_EXPRESSION | ALLOW_TS_TYPE_ASSERTION. Copy type — passed by value everywhere, never stored on the parser.

### Decisive source
```rust
/// Whether `in` should be counted in a binary expression.
/// This is for `for...in` statements to prevent ambiguity.
/// Corresponds to `[+In]` in the EcmaScript spec if true
const INCLUDE_IN: Self = ...;

// for-head initializer disables `in` so the head can't swallow the loop's own `in`
let init_expr = parse_expression(
    p,
    ExpressionContext::default()
        .and_include_in(false)
        .and_object_expression_allowed(has_l_paren),
);
```

**Flow:** every production that parses an expression takes a context parameter → sub-calls derive a new context via `and_*` builders (add flag if true, remove if false) → leaf checks like `T![in] => context.is_in_included()` (:524-527) or `T!['{'] if context.is_object_expression_allowed()` (:1353) consult it.
**Invariant:** The context is *derived per call site*, never mutated in place, and never global state — two sibling calls at the same depth may legally see different contexts (e.g. conditional consequent vs alternate). Forgetting to clear `INCLUDE_IN` in a for-head makes `for (a in b;;)` unparseable; forgetting to re-enable it in loop bodies breaks every `"x" in obj`.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/for_in.js` / `for_of.js` snapshots (`for((true,"selectionStart" in true);;) {}` and `for(["a" in {}];;) {}` parse because heads disable `in`, bodies restore it).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "ExpressionContext INCLUDE_IN and_include_in", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the immutable derived-context bitflags as the mechanism for spec bracketed-parameters; adapt the specific flags; omit flags your language doesn't need. Do not convert it to mutable parser state — the whole point is per-call-site derivation.
