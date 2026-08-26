<!-- capsule-v2 -->
# Type-predicate return type + reserved type names — how does `a is string` / `asserts a` get recognized at the return-type position without confusing `type asserts = string`?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What exact lookahead selects `TS_PREDICATE_RETURN_TYPE` / `TS_ASSERTS_RETURN_TYPE` over a plain type, and where do the `asserts`-without-`is` and line-break rules bind?

## parse_ts_return_type + parse_ts_type_predicate
**Path/Symbol:** `crates/biome_js_parser/src/syntax/typescript/types.rs:parse_ts_return_type` (:1836-1846), `parse_ts_type_predicate` (:1854-1879).
**Signature:** `fn parse_ts_return_type(p: &mut JsParser, context: TypeContext) -> ParsedSyntax`; predicate name accepts `this` or a reference identifier.
**Data Shape:** `TS_PREDICATE_RETURN_TYPE` (`x is T`) vs `TS_ASSERTS_RETURN_TYPE` (`asserts x [is T]`, condition node = `TS_ASSERTS_CONDITION`).

### Decisive source
```rust
let is_asserts_predicate = p.at(T![asserts]) && (is_nth_at_identifier(p, 1) || p.nth_at(1, T![this]));
let is_is_predicate = (is_at_identifier(p) || p.at(T![this])) && p.nth_at(1, T![is]);

if !p.has_nth_preceding_line_break(1) && (is_asserts_predicate || is_is_predicate) {
    parse_ts_type_predicate(p, context)
} else {
    parse_ts_type(p, context)
}
```
Inside the predicate:
```rust
let is_asserts = p.eat(T![asserts]);
parse_ts_this_type(p).or_else(|| parse_reference_identifier(p)).unwrap();
if is_asserts && p.at(T![is]) { /* TS_ASSERTS_CONDITION wraps 'is T' */ }
else if !is_asserts { p.expect(T![is]); /* mandatory for plain predicates */ }
```

**Flow:** at the `:` return position, two-token probes decide: `asserts`+ident/this ⇒ asserts form; ident/this+`is` ⇒ predicate form — both gated on no preceding line break before the second token (ASI safety in member positions like `foo(test: string): I\n is(): boolean;`). Plain types otherwise.
**Invariant:** The line-break check is what lets `type asserts = string;` and `() => asserts;` still parse as references/`any`-ish types — `asserts` alone never forces the predicate reading. `x is Y` requires the subject to be `this` or an identifier, NOT an arbitrary type. For asserts, `is` is optional but when present it must wrap into `TS_ASSERTS_CONDITION`.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/ts_return_type_asi.ts` (`foo(test: string): I` newline `is(): boolean;`) and `ok/ts_function_type.ts` (`(a: any) => a is string`, `type D = () => asserts;`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_ts_return_type asserts is predicate line break", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt two-token probe + line-break gate for contextual return-shape selection; adapt kinds; omit message text.
