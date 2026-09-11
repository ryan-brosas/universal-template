<!-- capsule-v2 -->
# Ambient declare gate — which lookahead rules make `declare` unambiguous against identifiers and `using` declarations?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How do I recognize a TS ambient declaration without misfiring on `declare` used as a plain identifier, and how does the ambient flag propagate?

## is_at_ts_declare_statement + parse_ts_declare_statement
**Path/Symbol:** `crates/biome_js_parser/src/syntax/typescript/statement.rs:parse_ts_declare_statement` (:233-250), `is_at_ts_declare_statement` (:253-265); state push `crate::state::EnterAmbientContext`; clause dispatcher `auxiliary.rs:parse_declaration_clause` (see declaration-clause-gate capsule).
**Signature:** `fn is_at_ts_declare_statement(p: &mut JsParser) -> bool` — pure probe; parse fn wraps body in `p.with_state(EnterAmbientContext, |p| parse_declaration_clause(p, stmt_start_pos))`.
**Data Shape:** Three negative guards then delegation: (1) line break between `declare` and next token ⇒ false (ASI: it's an expression statement on `declare`); (2) `declare using x` ⇒ false (that's an error surface tested separately, NOT an ambient declaration); (3) `declare await using x` ⇒ false; otherwise `is_nth_at_declaration_clause(p, 1)` decides.

### Decisive source
```rust
pub(crate) fn is_at_ts_declare_statement(p: &mut JsParser) -> bool {
    if !p.at(T![declare]) || p.has_nth_preceding_line_break(1) {
        return false;
    }
    if matches!(p.nth(1), T![using])
        || (matches!(p.nth(1), T![await]) && matches!(p.nth(2), T![using]))
    { return false; }
    is_nth_at_declaration_clause(p, 1)
}
```
Ambient-state wrap:
```rust
let stmt_start_pos = p.cur_range().start();
let m = p.start();
p.expect(T![declare]);
p.with_state(EnterAmbientContext, |p| {
    parse_declaration_clause(p, stmt_start_pos).or_add_diagnostic(p, expected_declare_statement)
});
Present(m.complete(p, TS_DECLARE_STATEMENT))
```

**Flow:** statement dispatch sees `T![declare]` + probe true → exclusive-syntax wrapper (see ts-exclusive-dialect-gate) → inside, `EnterAmbientContext` flips the parser-state bit that downstream checks read via `p.state().in_ambient_context()` (e.g., decorated-class rejection in the declaration-clause path) → the inner clause parser handles function/class/const/etc. bodies with initializer bans.
**Invariant:** The line-break guard must precede everything — `declare\nfunction f() {}` is TWO statements under ASI, not an ambient declaration. `using`/`await using` exclusion exists because those forms are their own error tests; folding them into the ambient path would mask the intended diagnostics. The ambient flag is scoped by `with_state` (auto-restored) — a porter who sets it manually leaks ambient mode into following statements.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/ts_declare_using.ts` (`declare using x: null` / `declare await using x: null` errors) plus `…/error/ts_declare_const_initializer.ts` vs `…/ok/ts_declare_const_initializer.ts` pair pinning the ambient initializer ban (`declare module test { const X; }` ok / initialized not).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "EnterAmbientContext is_at_ts_declare_statement", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-guard probe + scoped ambient state; adapt the clause table behind it; omit `using` exclusions in hosts without explicit-resource-management syntax.
