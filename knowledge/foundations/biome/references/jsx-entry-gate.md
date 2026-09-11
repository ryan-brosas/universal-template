<!-- capsule-v2 -->
# JSX-vs-type-assertion entry gate — how does `<div>a</div>` win over `<string>b` type assertions in script mode with only two tokens of lookahead?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What is the minimal gate deciding JSX tag expression vs TS angle-bracket assertion, and why are TSX generics parsed WITHOUT the expression-position speculation?

## parse_jsx_tag_expression entry + opening-tag type-args note
**Path/Symbol:** `crates/biome_js_parser/src/syntax/jsx/mod.rs:parse_jsx_tag_expression` (:53-79), generic note at `parse_any_jsx_opening_tag` (:159-168 pre-drift; now :218-228 after the pass-15 Astro insert below shifted everything ≥:232). **Pass-15 erratum:** this function now contains the checkpoint/abandon/rewind speculative-completion tail (`astro-implicit-fragment-reparse`) BEFORE its `Present(...)` return; entry gate below is unchanged.
**Signature:** `fn parse_jsx_tag_expression(p: &mut JsParser) -> ParsedSyntax`.
**Data Shape:** Gate: at `<` AND (`>` | identifier-or-keyword | metavariable) — else Absent (falls back to comparison/assertion paths).

### Decisive source
```rust
// jsx_or_type_assertion test cases this decides:
// let a = <div>a</div>;   // JSX
// let b = <string>b;      // type assertion
// let d = <div>a</div>/;  // ambiguous: JSX or "type assertion a less than regex /div>/". Probably JSX.
if !p.nth_at(1, T![>]) && !is_nth_at_identifier_or_keyword(p, 1) && !is_nth_at_metavariable(p, 1) {
    return Absent;
}
```
```rust
// Don't parse type arguments in JS because it prevents us from doing better error recovery in case the
// `>` token of the opening element is missing:
// `<test <inner></test>` The `inner` is its own element and not the type arguments
if TypeScript.is_supported(p) {
    let _ = parse_ts_type_arguments(p, TypeContext::default());   // committed, not speculative
}
```

**Flow:** expression parser hits `<` → two-token gate picks JSX vs everything else → inside a real tag, TSX type arguments parse *committed* after the element name. In JS files they never attempt.
**Invariant:** The gate is deliberately shallow: `<5` can't start either construct; `<string>b` in script mode reaches the assertion path because the *assertion* parser claims it first by feature-gating, not by deeper lookahead here. Generic type args on elements must NOT use the speculative `parse_ts_type_arguments_in_expression` — speculation would rewind past a legitimately missing `>` and misattach `<inner>` as type arguments in `<test <inner></test>`. Committed-with-diagnostics beats speculative-happy-path for error recovery quality.
**Probe:** `error/jsx_or_type_assertion.jsx` (the four-way ambiguity incl. trailing `/`) and `ok/tsx_element_generics_type.jsx` (`<Generic<true>></Generic>`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "jsx tag expression type arguments element generics recovery", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt shallow entry gates that defer to feature-gated claimants, plus committed over speculative parsing where error recovery matters more than speed; adapt to host's assertion syntax; omit nothing portable.
