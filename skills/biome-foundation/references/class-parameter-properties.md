<!-- capsule-v2 -->
# Constructor parameter properties — how do TS parameter modifiers nest a second modifier list *inside* a single parameter?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** `constructor(@foo private readonly x: string)` is one parameter that carries decorators, its own modifier list, and a nested formal parameter — how is it structured so validation reuses the class-member modifier machinery?

## parse_constructor_parameter + TS_PROPERTY_PARAMETER
**Path/Symbol:** `crates/biome_js_parser/src/syntax/class.rs:parse_constructor_parameter` (:1603-1691), `parse_constructor_parameter_list` (:1581-1598), modifier reuse via `parse_class_member_modifiers(p, true)` (:1651), legality via `TS_PROPERTY_PARAMETER` arm of `check_class_member_modifier` (:2372-2386).
**Signature:** `fn parse_constructor_parameter(p: &mut JsParser, context: ExpressionContext) -> ParsedSyntax`.
**Data Shape:** Node shape: `TS_PROPERTY_PARAMETER` wraps `[decorator_list?] [modifier_list] [formal_parameter]`. The decorator list parsed at parameter level becomes the OUTER list; the inner formal parameter deliberately gets `Absent` decorators to avoid duplication.

### Decisive source
```rust
let decorator_list = parse_parameter_decorators(p);
if is_nth_at_modifier(p, 0, true) {          // constructor_parameter=true changes the lookahead:
    let property_parameter = decorator_list.or_else(|| empty_decorator_list(p)).precede(p);
    let modifiers = parse_class_member_modifiers(p, true);   // same validator as class members
    parse_formal_parameter(p, Absent, ParameterContext::ParameterProperty, context, ...)
        .or_add_diagnostic(p, expected_binding);
    let kind = if modifiers.validate_and_complete(p, TS_PROPERTY_PARAMETER) {
        TS_PROPERTY_PARAMETER } else { JS_BOGUS_PARAMETER };
    Present(property_parameter.complete(p, kind))
} else {
    parse_any_parameter(p, decorator_list, ParameterContext::ClassImplementation, ...)
        .map(|mut param| { if param.kind(p) == TS_THIS_PARAMETER {
            p.error("A constructor cannot have a 'this' parameter.");
            param.change_to_bogus(p); } param })
}
```

**Flow:** parse parameter decorators → lookahead for modifier-then-name (the `constructor_parameter` flag makes `{`/`[` after the modifier also count, since destructuring parameters are legal but can't be property params — they error later) → wrap: precede with decorator marker → member-style modifier list → inner formal parameter → complete as property-parameter or bogus-parameter → else ordinary parameter path with constructor-specific `this` rejection.
**Invariant:** The modifier whitelist for parameters differs from members (only accessibility/override/readonly pass; :2372-2386) yet runs through the identical `validate_and_complete` — one code path, two policy tables keyed by target kind. `is_nth_at_modifier`'s line-break rule is waived only for `static`; every other modifier must stay on the same line as what follows or it's treated as a name (`is_nth_at_modifier`, :1722-1753).
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/ts_property_parameter.ts` (pins `private x`, `readonly w`, `...rest` mixes) and `error/ts_property_parameter_pattern.ts` (`private { x, y }` rejected).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_constructor_parameter TS_PROPERTY_PARAMETER", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt wrapper-node composition (decorators + modifiers + inner production) with shared validators over per-target policies; adapt whitelists; omit the this-parameter rejection if your language lacks TS's `this` params. Coverage caveat: full-mode index, metadata_match.
