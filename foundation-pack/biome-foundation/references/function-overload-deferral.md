<!-- capsule-v2 -->
# Function overload deferral — how do you parse `function f(a: string): void;` vs an implementation when body presence is only known after the parameter list?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does one parse function declarations so that a TS overload signature (no body, `;`) and a full implementation share one grammar path without backtracking?

## parse_function — single-pass body-absence fork
**Path/Symbol:** `crates/biome_js_parser/src/syntax/function.rs:parse_function` (:206-324), fork at :286-308.
**Signature:** `fn parse_function(p: &mut JsParser, m: Marker, kind: FunctionKind) -> CompletedMarker` with `FunctionKind::{Declaration{single_statement_context}, Expression, ExportDefault}`.
**Data Shape:** Consumes marker `m` opened by the caller. Emits either `TS_DECLARE_FUNCTION_DECLARATION` / `TS_DECLARE_FUNCTION_EXPORT_DEFAULT_DECLARATION` or the kind-mapped declaration/expression kind; generator `*` range captured before id parse for the overload-generator error.

### Decisive source
```rust
let parameter_context = if !kind.is_expression() && TypeScript.is_supported(p) {
    // It isn't known at this point if this is a function overload definition (body is missing)
    // or a regular function implementation. Let's go with the laxer of the two.
    ParameterContext::Declaration
} else {
    ParameterContext::Implementation
};
// ... parameters + return type parsed ...
if body.is_absent()
    && TypeScript.is_supported(p)
    && is_semi(p, 0)
    && !kind.is_in_single_statement_context()
    && !kind.is_expression()
{
    p.eat(T![;]);
    if let Some(generator_range) = generator_range {
        p.error(p.err_builder("An overload signature cannot be declared as a generator.", generator_range));
    }
    // completes TS_DECLARE_FUNCTION_DECLARATION(_EXPORT_DEFAULT)
} else { /* complete kind.into(); async/generator-in-single-stmt-context → bogus */ }
```

**Flow:** eat optional `async` (flag) → expect `function` → capture+eat `*` (flag + range) → `parse_function_id` (Expression re-enters with own flags via `EnterFunction`, declarations inherit parent's) → TS type params (`allow_const_modifier(true)`) → choose laxer `ParameterContext::Declaration` when classification unknown → parameter list → TS return type → **then** branch on body absence: absent + TS + at `;` + not expression/single-stmt ⇒ consume `;`, emit declare-kind (generator error retro-fires from captured range); otherwise require body and demote to bogus if async/generator in single-statement context.
**Invariant:** Classification never rewinds. The parameter list is always parsed under the *laxer* Declaration context whenever body presence is undecidable at that point — porting it as Implementation-first breaks every valid overload. Overload detection = exactly `{body absent ∧ TS ∧ next-is-;}`; anything else with no body stays the normal kind with `expected_function_body` diagnostic.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/ts_function_overload.ts(.snap)` (overload then implementation pairs, incl. `function no_semi(a: string)` followed by implementation without blank line) and `error/ts_function_overload_generator.ts` (pins "An overload signature cannot be declared as a generator" while still parsing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_function ParameterContext Declaration overload", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the deferred-classification pattern (lax context now, kind decided by trailing `;`/body presence) for any parser facing overloads/signatures; adapt kind names to host AST; omit Biome-specific error wording. Ambient variant note: `parse_ambient_function` (:388-472) parses async/generator but *errors and continues* rather than failing, completing `JS_BOGUS_STATEMENT` only for async.
