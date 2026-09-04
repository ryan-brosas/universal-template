<!-- capsule-v2 -->
# Type-parameter list quirks — why is `type A<> = {}` an error but `f<>` in other positions legal, and how do modifiers, constraints, and defaults order inside `<…>`?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What governs empty type-parameter lists, trailing commas, and the modifiers→name→constraint→default ordering that recovery must preserve?

## parse_ts_type_parameters + TsTypeParameterList
**Path/Symbol:** `crates/biome_js_parser/src/syntax/typescript/types.rs:parse_ts_type_parameters` (:230-246), `TsTypeParameterList` (:248-283), `parse_ts_type_parameter` (:389-403), clauses (:526-550).
**Signature:** `fn parse_ts_type_parameters(p: &mut JsParser, context: TypeContext) -> ParsedSyntax`; `ParseSeparatedList` with `allow_trailing_separating_element() == true` (contrast type *arguments*: false) and recovery set `{'>', ',', ident, yield, await}` + line-break.
**Data Shape:** `TS_TYPE_PARAMETERS` ⊃ `TS_TYPE_PARAMETER_LIST` ⊃ `TS_TYPE_PARAMETER` = `[modifier list][name][TS_TYPE_CONSTRAINT_CLAUSE extends …][TS_DEFAULT_TYPE_CLAUSE = …]`.

### Decisive source
```rust
let m = p.start();
p.bump(T![<]);
if p.at(T![>]) && !context.is_in_type_or_interface_declaration() {
    p.error(expected_ts_type_parameter(p, p.cur_range()));
}
TsTypeParameterList(context).parse_list(p);
p.expect(T![>]);
```
```rust
fn parse_ts_type_parameter(p: &mut JsParser, context: TypeContext) -> ParsedSyntax {
    let m = p.start();
    parse_ts_type_parameter_modifiers(p, context).ok();   // in/out/const — see TypeContext capsule
    let name = parse_ts_type_parameter_name(p);
    parse_ts_type_constraint_clause(p, context).ok();     // extends T  (context threaded!)
    parse_ts_default_type_clause(p).ok();                 // = T        (resets to default context)
    if name.is_absent() { m.abandon(p); Absent } else { Present(m.complete(p, TS_TYPE_PARAMETER)) }
}
```

**Flow:** gate on `is_nth_at_ts_type_parameters` (`<`) → empty-list error suppressed inside type/interface declarations (`type A<> = {}` errors; the declaration-position exemption exists because interfaces legitimately reach here with zero params via other paths) → separated list → expect `>`.
**Invariant:** Ordering modifiers→name→constraint→default is structural (TS grammar); a parameter with no NAME abandons its marker entirely — modifiers/constraints parsed before the absent name dissolve rather than becoming bogus orphans. Constraint clauses thread the incoming TypeContext; the default clause deliberately resets to `TypeContext::default()`.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/ts_type_parameters_incomplete.ts` (`type A<T`) and `ok/ts_type_parameters.ts` (`<T extends string | number = number>`, `<>` forms).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_ts_type_parameters TsTypeParameterList allow_trailing_separating_element", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ordered single-pass parameter parsing with name-presence abandonment and position-gated empty-list diagnostics; adapt clause kinds; omit token spellings.
