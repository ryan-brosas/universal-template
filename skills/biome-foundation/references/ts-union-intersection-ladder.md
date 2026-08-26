<!-- capsule-v2 -->
# Union/intersection ladder — how do leading-operator unions (`| A | B`) and single-element non-wrapping work without a precedence-climbing loop?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does the type grammar build union/intersection nodes only when an operator actually appears, while keeping intersection binding tighter than union?

## IntersectionOrUnionType parameterized ladder
**Path/Symbol:** `crates/biome_js_parser/src/syntax/typescript/types.rs:IntersectionOrUnionType` (:634-672), `parse_ts_union_or_intersection_type` (:674-710), `eat_ts_union_or_intersection_type_elements` (:712-725).
**Signature:** `enum IntersectionOrUnionType {Union, Intersection}` supplying `operator()`, `list_kind()`, `kind()`, `parse_element()`; recursion: union elements = intersections, intersection elements = primary types.
**Data Shape:** `TS_UNION_TYPE` ⊃ `TS_UNION_TYPE_VARIANT_LIST`; `TS_INTERSECTION_TYPE` ⊃ `TS_INTERSECTION_TYPE_ELEMENT_LIST`. Single element with no operator ⇒ the element itself, unwrapped.

### Decisive source
```rust
// Leading operator: `& A & B`
if p.at(ty_kind.operator()) {
    let m = p.start();
    p.bump(ty_kind.operator());
    let list = p.start();
    ty_kind.parse_element(p, context).or_add_diagnostic(p, expected_ts_type);
    eat_ts_union_or_intersection_type_elements(p, ty_kind, context);
    list.complete(p, ty_kind.list_kind());
    Present(m.complete(p, ty_kind.kind()))
} else {
    let first = ty_kind.parse_element(p, context);
    if p.at(ty_kind.operator()) {
        let list = first.precede(p);                       // wrap first elem retroactively
        eat_ts_union_or_intersection_type_elements(p, ty_kind, context);
        let completed_list = list.complete(p, ty_kind.list_kind());
        let m = completed_list.precede(p);
        Present(m.complete(p, ty_kind.kind()))
    } else {
        first // Not a union or intersection type
    }
}
```

**Flow:** parse at one level → if next token is this level's operator, `precede` the already-completed first element into a retroactive list node, then loop bumping operator + parsing next-level element. Union level calls intersection level; intersection calls primary — that call chain IS the precedence (no explicit binding-power table needed for two levels).
**Invariant:** The retroactive-wrap trick (`first.precede(p)` after the element is complete) is what allows zero backtracking: you never know a union started until the *second* operand position. A porter who starts the list marker eagerly wraps every plain type in a singleton union. Mixed `A & B | C` works because each union element re-enters the whole intersection ladder.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/ts_union_type.ts` (`type B = | A | void | null;` leading-operator form) and `ok/ts_intersection_type.ts`-equivalents (`type C = A & C | C;` mixed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_ts_union_or_intersection_type precede variant list", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt two-level parameterized ladder + retroactive list wrapping for right-associative-looking binary operators in any grammar; adapt kinds/operators; omit nothing portable.
