<!-- capsule-v2 -->
# Literal-type rekind — how does `type A = -5` reuse expression parsing yet produce TS literal *types* instead of expression nodes?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How are number/bigint/string/boolean/null literal types parsed via the expression parser without leaving expression nodes in the tree, including the negative-literal special case?

## parse_ts_literal_type change_kind / undo_completion
**Path/Symbol:** `crates/biome_js_parser/src/syntax/typescript/types.rs:parse_ts_literal_type` (:1568-1606), dispatch entry in `parse_ts_non_array_type` (:876-945).
**Signature:** `fn parse_ts_literal_type(p: &mut JsParser) -> ParsedSyntax`; regex literals explicitly Absent (not valid types).
**Data Shape:** Maps `JS_{NUMBER,BIGINT,STRING,BOOLEAN,NULL}_LITERAL_EXPRESSION → TS_*_LITERAL_TYPE`. Negative form: `-` + number/bigint only (`T![-] if p.nth_at(1, JS_NUMBER_LITERAL)`).

### Decisive source
```rust
if p.at(T![-]) && p.nth_at(1, JS_NUMBER_LITERAL) {
    let m = p.start();
    p.bump(T![-]);
    let number_expr = parse_number_literal_expression(p)
        .or_else(|| parse_big_int_literal_expression(p))
        .unwrap();
    let type_kind = match number_expr.kind(p) {
        JS_NUMBER_LITERAL_EXPRESSION => TS_NUMBER_LITERAL_TYPE,
        JS_BIGINT_LITERAL_EXPRESSION => TS_BIGINT_LITERAL_TYPE,
        _ => unreachable!(),
    };
    // Inline the number or big int literal into the number/big int literal type
    number_expr.undo_completion(p).abandon(p);   // dissolve the expression node entirely
    return Present(m.complete(p, type_kind));    // '-' + literal live inside ONE type node
}
parse_literal_expression(p).map(|mut expression| {
    let type_kind = match expression.kind(p) { … };
    expression.change_kind(p, type_kind);        // rename in place: expr → type
    expression
})
```

**Flow:** positive path: parse the ordinary literal *expression*, then `change_kind` renames the completed node to its type counterpart — no re-parse, no marker surgery. Negative path: open a fresh marker, bump `-`, parse the literal, then `undo_completion().abandon()` dissolves the expression so `-5n` becomes a single `TS_BIGINT_LITERAL_TYPE`.
**Invariant:** The kind-mapping must stay exhaustive over exactly the five whitelisted expression kinds (`unreachable!` guards it). `change_kind` is safe only because literal expressions and literal types have identical child structure; any host whose type nodes carry extra slots must use the undo/abandon route instead. The negative branch accepts bigint but NOT other unary-prefixed types.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/ts_literal_type.ts` (`-5`, `5n`, `-5n`, `"abvcd"`, `true`, `null`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_ts_literal_type undo_completion change_kind", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt parse-as-expression + in-place rekind for grammar nodes that share shape across planes; adapt kind tables; omit nothing portable. Third distinct instance of Biome's event-surgery pattern (with assignment-event-rewrite.md's dropped events and pattern-kind-traits' completion absorption).
