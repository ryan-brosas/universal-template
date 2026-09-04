<!-- capsule-v2 -->
# Label / breakable state machine — how `break foo` legality is known while parsing the jump, not the target

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does the parser validate label references and break/continue placement without a post-parse pass?

## WithLabel + LabelledItem + EnterBreakable parser state
**Path/Symbol:** `crates/biome_js_parser/src/syntax/stmt.rs:parse_labeled_statement` (:426-493), `parse_break_statement` (:601-638), `parse_continue_statement` (:658-708), loop wrappers (`parse_while_statement` :1031, `parse_do_statement` :1568, `parse_for_statement` :1765, switch :1967); state types in `crates/biome_js_parser/src/state.rs` (`WithLabel`, `LabelledItem`, `EnterBreakable`, `BreakableKind`).
**Signature:** `p.with_state(WithLabel(String, LabelledItem::{Iteration(TextRange), Other(TextRange)}), |p| ...)`; `p.with_state(EnterBreakable(BreakableKind::{Iteration, Switch}), |p| ...)`.
**Data Shape:** Parser state carries a label stack (each entry = name + kind + declaring range) plus a breakable-kind stack; jump statements read both at parse time. Errors are decided in the jump-statement parser itself and demote the completed statement to `JS_BOGUS_STATEMENT`.

### Decisive source
```rust
let error = if !p.has_preceding_line_break() && is_at_identifier(p) {
    let label_name = p.cur_text();
    match p.state().get_labelled_item(label_name) {
        Some(_) => None,
        None => Some(p.err_builder(format!("Use of undefined statement label `{label_name}`"), p.cur_range())
            .with_hint("This label is used, but it is never defined")),
    } // continue additionally rejects Some(LabelledItem::Other(_)):
} else if !p.state().continue_allowed() { /* "only within an enclosing for/while/do while" */ }
// registration side: labelled body parsed under WithLabel; duplicate labels error but parsing continues;
// nested same-name label RE-USES parent context to keep checking deeper duplicates:
fn parse_body(...) { if is_at_identifier(p) && p.nth_at(1, T![:]) && StrictMode.is_unsupported(p) {
    p.parse_labeled_statement(p, context) /* re-use parent context */ } else { parse_statement(p, StatementContext::Label) } }
```

**Flow:** `label:` → register `WithLabel(name, Iteration iff cur ∈ {for,do,while}, range)` → parse body → duplicate detection consults existing stack entries (error with first-use detail, still parses). Loops/switch wrap their bodies in `EnterBreakable(kind)` so bare `break`/`continue` legality is a stack query (`break_allowed()` allows Switch too; `continue_allowed()` only Iteration). Label lookup happens BEFORE the label identifier is consumed via `parse_identifier(p, JS_LABEL)` so the diagnostic can quote source text.
**Invariant:** The label table is SCOPED by RAII state push/pop — a label registered inside a loop body vanishes after it, which is what makes `while (true) { break foo; }` an undefined-label error without any symbol table. `Iteration` vs `Other` classification happens at REGISTRATION from the next token, not when `continue` arrives.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/labeled_statement.js` + `error/double_label.js` (duplicate labels), `ok/break_stmt.js`/`error/break_stmt.js` (undefined label, function-body break), `ok/async_continue_stmt.js` (label named `async`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "get_labelled_item EnterBreakable BreakableKind WithLabel LabelledItem", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the state-stack pattern for any scoped validity question (labels, `arguments`, `new.target`) in hand-written parsers; adapt BreakableKind enum to host grammar; omit exact diagnostics.
