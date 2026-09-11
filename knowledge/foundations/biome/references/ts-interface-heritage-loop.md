<!-- capsule-v2 -->
# Interface heritage loop — why does the parser LOOP over extends/implements clauses and how are illegal ones kept for recovery?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How should a declaration parser handle repeated or forbidden heritage clauses so recovery stays positioned without dropping diagnostics?

## eat_interface_heritage_clause
**Path/Symbol:** `crates/biome_js_parser/src/syntax/typescript/statement.rs:eat_interface_heritage_clause` (:353-380); clause builders `parse_ts_extends_clause` (:386-395, completes `TS_EXTENDS_CLAUSE` via `expect_ts_type_list`), `parse_ts_implements_clause` (typescript.rs, same shape with TS_IMPLEMENTS_CLAUSE).
**Signature:** `fn eat_interface_heritage_clause(p: &mut JsParser)` — consumes any number of `extends`/`implements` clauses at the current position, attaching them to the active interface node.
**Data Shape:** Loop state is a single `first_extends: Option<CompletedMarker>`; implements clauses are ALWAYS parsed then errored; duplicate extends keep both nodes but error on the second+.

### Decisive source
```rust
loop {
    if p.at(T![extends]) {
        let extends = parse_ts_extends_clause(p).expect(…);
        if let Some(first_extends) = first_extends.as_ref() {
            p.error(p.err_builder("'extends' clause already seen.", extends.range(p))
                .with_detail(first_extends.range(p), "first 'extends' clause"));
        } else { first_extends = Some(extends); }
    } else if p.at(T![implements]) {
        let implements = parse_ts_implements_clause(p).expect(…);
        p.error(p.err_builder(
            "Interface declaration cannot have 'implements' clause.", implements.range(p)));
    } else { break; }
}
```
Empty-list diagnostic inside expect_ts_type_list (`crates/biome_js_parser/src/syntax/typescript.rs:102-124`):
```rust
if parse_ts_reference_type(p, TypeContext::default()).is_absent() {
    p.error(p.err_builder(format!("'{clause_name}' list cannot be empty."), start..start))
}
// per trailing comma:  "Trailing comma not allowed." at comma_range, then break
```

**Flow:** interface body assembly: `interface` → name (`TsIdentifierContext::Type`) → type parameters (with `allow_in_out` + `type_or_interface_declaration` flags set) → THIS loop → `{` → `TypeMembers::default().parse_list(p)` → `}`. Each loop iteration parses one full clause even when illegal, so the cursor lands past it and the next iteration can catch another.
**Invariant:** Parse-then-error (not skip) keeps every illegal clause in the tree AND advances past it — a porter who breaks instead of consuming turns one bad clause into a cascade inside the member list. Duplicate-extends errors carry a WITH-DETAIL secondary range pointing at the first occurrence. The empty type-list diagnostic anchors at a zero-width range (start..start), which downstream renderers show as "expected here" — do not widen it.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/ts_interface_heritage_clause_error.ts` (`interface B implements A {}`, `interface C extends A extends B {}`, `interface D extends {}`, `interface E extends A, {}`) and `…/ok/ts_export_default_interface.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "eat_interface_heritage_clause expect_ts_type_list", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the parse-illegal-clauses-anyway loop with first-occurrence detail; adapt clause keyword sets; omit the implements arm in hosts where interfaces have no class counterpart.
