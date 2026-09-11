<!-- capsule-v2 -->
# Single-statement demotion — why `if (x) const a = 1` becomes bogus after parsing succeeds

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How are "lexical declarations and labelled/class/function bodies illegal in a single-statement context" enforced when the grammar has already consumed the tokens?

## StatementContext + post-hoc change_to_bogus
**Path/Symbol:** `crates/biome_js_parser/src/syntax/stmt.rs:StatementContext` (:130-150), enforcement in `parse_variable_statement` (:1131-1146), `parse_labeled_statement` (:474-484).
**Signature:** `pub(crate) enum StatementContext { If, Label, Do, While, With, For, StatementList }` with `is_single_statement() == !matches!(self, Self::StatementList)`; statement parsers receive it as a plain parameter.
**Data Shape:** The statement is parsed normally, completed as the correct kind (`JS_VARIABLE_STATEMENT`, body of `JS_LABELED_STATEMENT`), then demoted: `statement.change_to_bogus(p)` + one diagnostic. No rewind, no speculation.

### Decisive source
```rust
if !is_var && context.is_single_statement() {
    // if (true) let a;   while (true) const b = 5;
    p.error(p.err_builder("Lexical declaration cannot appear in a single-statement context",
        statement.range(p)).with_hint("Wrap this declaration in a block statement"));
    statement.change_to_bogus(p);
}
// labelled variant:
Some(mut body) if context.is_single_statement_context() && body.kind(p) == JS_FUNCTION_DECLARATION => {
    // if (true) label1: label2: function a() {}
    p.error(... "Labelled function declarations are only allowed at top-level or inside a block" ...);
    body.change_to_bogus(p);
}
```

**Flow:** Parent passes its context down (`parse_statement(p, StatementContext::If)` from the if-body slot :970/:976); `var` is exempt from the lexical ban (`!is_var` gate — hoisting makes `if (true) var a;` legal, pinned by `ok/hoisted_declaration_in_single_statement_context.js`), `let/const/using/await using` are not. The same completed-marker demotion pattern covers labelled function bodies.
**Invariant:** Legality is decided by CONTEXT THREADING, not lookahead: the child never re-checks what precedes it. A porter who instead tries to detect these cases at dispatch time must replicate every caller site; missing one silently accepts `while (x) const b = 5`. Demotion keeps the CST lossless — the tokens stay in a bogus node, so formatting/round-trip survive.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/lexical_declaration_in_single_statement_context.js(.snap)` vs `ok/hoisted_declaration_in_single_statement_context.js`, plus `error/labelled_function_decl_in_single_statement_context.js`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "StatementContext single_statement change_to_bogus lexical declaration", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt context-threading + post-hoc demotion for any legality rule that depends on the parent production (also: `await using` async-context check :1148-1163 uses identical shape); adapt kind names; omit Biome's hint wording.
