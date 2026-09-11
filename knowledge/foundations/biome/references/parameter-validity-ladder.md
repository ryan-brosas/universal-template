<!-- capsule-v2 -->
# Parameter validity ladder — where do optional-`?`, setter, rest-parameter, and parameter-property constraints attach, and why does the formal-parameter path checkpoint+rewind on a failed binding?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How are per-parameter TS/JS legality rules ordered so each error fires once against the right context, and how does a failed binding pattern unwind cleanly inside a parameter list?

## parse_formal_parameter + parse_rest_parameter ladders
**Path/Symbol:** `crates/biome_js_parser/src/syntax/function.rs:parse_formal_parameter` (:1184-1295), `parse_rest_parameter` (:1038-1101), `ParameterContext` enum (:1117-1169), `skip_parameter_start` (:1301-1315).
**Signature:** `fn parse_formal_parameter(p: &mut JsParser, decorator_list: ParsedSyntax, parameter_context: ParameterContext, expression_context: ExpressionContext, type_context: TypeContext) -> ParsedSyntax`; `ParameterContext ∈ {ClassImplementation, Implementation, Declaration, Setter, ClassSetter, Arrow, ParameterProperty}`.
**Data Shape:** Local `valid` flag accumulates violations; parameter completes as `JS_FORMAL_PARAMETER` and is demoted `change_to_bogus` iff `!valid`. Rest parameters track validity identically (`JS_REST_PARAMETER` → bogus on `?`, initializer, or trailing comma).

### Decisive source
```rust
// we use a checkpoint to avoid bogus nodes if the binding pattern fails to parse.
let checkpoint = p.checkpoint();
let m = decorator_list.or_else(|| empty_decorator_list(p)).precede(p);
if let Present(binding) = parse_binding_pattern(p, expression_context) {
    let mut valid = true;
    // '?' → ts_only error if unsupported; setters never optional ("A 'set' accessor cannot have an optional parameter.")
    // destructuring binding + ParameterProperty → "may not be declared using a binding pattern."
    // type annotation (TS-exclusive); then initializer:
    if let Present(initializer) = parse_initializer_clause(p, expression_context) {
        if valid && parameter_context.is_any_setter() && TypeScript.is_supported(p) { /* set accessor no initializer */ }
        else if is_optional && valid { /* "Parameter cannot have question mark and initializer" */ }
    }
    let mut parameter = m.complete(p, JS_FORMAL_PARAMETER);
    if !valid { parameter.change_to_bogus(p); }
    Present(parameter)
} else {
    m.abandon(p);
    p.rewind(checkpoint);   // ← no bogus node, no stray events for non-parameter junk
    Absent
}
```

**Flow:** decorators precede marker → try binding pattern → success: run ordered checks (`?` legality → pattern-in-parameter-property → annotation → initializer-vs-setter/optional) with single `valid` flag → complete → conditionally demote. Failure: abandon marker AND rewind checkpoint — distinguishing "not a parameter" from "invalid parameter" structurally.
**Invariant:** Context predicates, not string matching, gate every rule: only `is_any_setter()` forbids `?`/initializers; only `is_parameter_property()` forbids destructuring; only `is_arrow_function()` rejects `this` params (`parse_any_parameter`, :1014-1032). `skip_parameter_start` proves lookahead purity: a speculatively-parsed destructuring binding counts as "started a parameter" **only if diagnostics did not grow** (`diagnostics().len() == previous_error_count`). Rest-parameter ordering matters: trailing-comma check happens *after* completion, using the completed range.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/ts_formal_parameter_error.ts` (`x?: string = "test"`, `...rest = "init"`) plus `ok/ts_formal_parameter.ts` (legal `?`/default/annotation matrix); setter cases in class tests cited from `class-modifier-deferred-validation.md` probes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "ParameterContext setter formal parameter change_to_bogus", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the valid-flag→complete→demote shape and the checkpoint-rewind-on-absent split; adapt `ParameterContext` variants to host call sites; omit exact message strings. Complements `pattern-kind-traits.md` (binding grammar) by owning the *parameter wrapper's* legality ordering.
