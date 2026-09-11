<!-- capsule-v2 -->
# TypeContext flag ladder — how does the type grammar thread per-position permissions (conditional types, in/out, const, conditional-extends) without a second parser?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What is the mechanism that lets one recursive-descent type parser produce position-correct errors like "in/out modifier cannot appear here" instead of a generic syntax error?

## TypeContext bitflags
**Path/Symbol:** `crates/biome_js_parser/src/syntax/typescript/types.rs:TypeContext` (:48-136).
**Signature:** `struct TypeContext(BitFlags<ContextFlag>)` over `ContextFlag ∈ {DisallowConditionalTypes, AllowInOutModifier, AllowConstModifier, InConditionalExtends, TypeOrInterfaceDeclaration}`; combinators `and_allow_conditional_types(bool)`, `and_allow_in_out_modifier(bool)`, `and_allow_const_modifier(bool)`, `and_in_conditional_extends(bool)`, `and_type_or_interface_declaration(bool)` (each `and(flag, set)` = add-if-true/remove-if-false via BitOr/Sub impls :138-152).
**Data Shape:** Copy-type value passed *explicitly* down every type parse fn — not parser state. Default = conditionals allowed, in/out disallowed, const disallowed.

### Decisive source
```rust
if !p.has_preceding_line_break() && p.at(T![extends]) {
    let m = left.precede(p);
    p.expect(T![extends]);
    parse_ts_type(p, context.and_allow_conditional_types(false).and_in_conditional_extends(true)) // ← extends arm: nested conditionals banned, infer allowed
        .or_add_diagnostic(p, expected_ts_type);
    p.expect(T![?]);
    parse_ts_type(p, context).or_add_diagnostic(p, expected_ts_type);  // true/false arms: restored
    p.expect(T![:]);
    parse_ts_type(p, context).or_add_diagnostic(p, expected_ts_type);
    m.complete(p, TS_CONDITIONAL_TYPE)
}
```
And the consumer side (`parse_ts_type_parameter_modifiers` :451-521): `in`/`out` eaten then **abandoned with error** if `!context.is_in_out_modifier_allowed()`; same for `const`; duplicates error `modifier_already_seen` against the stored first range; `in` after an accepted `out` errors `modifier_must_precede_modifier`.
**Flow:** each grammar position derives a child context before recursing — constructor/function type params get `.and_allow_const_modifier(true)`, construct signatures add `.and_allow_in_out_modifier(true)`, mapped-type default clauses reset to `TypeContext::default()`, conditional extends arms set the pair shown above. The flags are checked at the exact token, so legality errors point at the right range.
**Invariant:** Context is threaded by value and never mutated globally; forgetting to re-widen on the true/false arms breaks `T extends U ? infer X ? A : B : C` nesting. `is_nth_at_type_parameter_modifier` (:444-449) is the shared predicate: `in|out|const` counts as a modifier only when NOT followed by `,` or `>` (so `<T, out>` stays a name list).
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/type_parameter_modifier.ts` (30+ negative positions incl. escaped `\u006E`) and `ok/type_parameter_modifier.ts` (legal matrix across class/interface/function/arrow/object members).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "TypeContext allow_in_out_modifier conditional types type parameter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt explicit value-threaded permission context for any dual-language grammar; adapt flag set; omit Biome's enumflags2 wiring. This is the repo's canonical answer to "position-sensitive grammar legality without a symbol table".
