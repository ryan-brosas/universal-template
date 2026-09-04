<!-- capsule-v2 -->
# Conditional-type extends arm + infer legality — how does `A extends B ? X : Y` nest correctly and why is `infer` legal only inside a conditional's extends clause?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** Which two context bits plus one line-break check make conditional types and `infer` constraints parse per the TS spec?

## parse_ts_type conditional fork + parse_ts_primary_type infer fork
**Path/Symbol:** `crates/biome_js_parser/src/syntax/typescript/types.rs:parse_ts_type` (:556-617), infer handling in `parse_ts_primary_type` (:727-811), `try_parse_constraint_of_infer_type` (:829-847).
**Signature:** `fn parse_ts_type(p: &mut JsParser, context: TypeContext) -> ParsedSyntax` — entry wraps everything in `p.with_state(EnterType, …)` (lexer switches to type lexing).
**Data Shape:** Precedence: constructor type → function type → union → (conditional if allowed) → primary. `TS_INFER_TYPE` completes inside conditional-extends; elsewhere `infer` becomes `TS_BOGUS_TYPE` + `infer_not_allowed` error.

### Decisive source
```rust
// conditional: only when allowed, and only on the SAME line
if !p.has_preceding_line_break() && p.at(T![extends]) { … complete TS_CONDITIONAL_TYPE }
// primary: infer
if p.at(T![infer]) {
    let m = p.start();
    p.expect(T![infer]);
    parse_ts_type_parameter_name(p).or_add_diagnostic(p, expected_identifier);
    try_parse_constraint_of_infer_type(p, context).ok();
    return if context.in_conditional_extends() {
        Present(m.complete(p, TS_INFER_TYPE))
    } else {
        let infer_type = m.complete(p, TS_BOGUS_TYPE);
        p.error(infer_not_allowed(p, infer_type.range(p)));
        Present(infer_type)
    };
}
```
The constraint probe speculatively parses `extends T` with conditionals **disabled** and rewinds via `try_parse` when `?` follows:
```rust
try_parse(p, |p| {
    let parsed = parse_ts_type_constraint_clause(p, context.and_allow_conditional_types(false)).expect(…);
    // Rewind if conditional types are allowed, and the parser is at the `?` token because
    // this should instead be parsed as a conditional type.
    if context.is_conditional_type_allowed() && p.at(T![?]) { Err(()) } else { Ok(Present(parsed)) }
}).unwrap_or(Absent)
```

**Flow:** `A extends B ? C : D`: left = union; same-line `extends` ⇒ reparse as conditional with extends-arm `{conditional-types disallowed, in_conditional_extends true}`. Inside that arm, `infer X` completes as `TS_INFER_TYPE`; its optional `extends U` constraint is itself parsed with conditionals off so `T extends (infer U extends number ? U : T) ? …` splits at the right `?`.
**Invariant:** Three coupled checks a porter will get wrong: (1) `has_preceding_line_break` before `extends` — a newline turns the conditional into a reference followed by an unexpected `extends`; (2) infer legality is keyed to `InConditionalExtends`, NOT to "inside any conditional"; (3) the infer-constraint speculation must disable nested conditionals or `(infer A) extends infer B ? …` mis-binds. Disallowed `infer` still yields a *Present* bogus node — the error must not swallow surrounding structure.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/ts_infer_type_allowed.ts` / `ok/ts_conditional_type.ts` vs `error/ts_infer_type_not_allowed.ts` (`{a: infer T}`, `` `${infer X}` `` etc.).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "infer not_allowed conditional_extends try_parse_constraint_of_infer_type", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-check contract (line-break gate, extends-arm flag pair, speculative rewindable infer constraint); adapt kinds; omit message text. Pairs with ts-type-context-ladder.md which owns the bit plumbing.
