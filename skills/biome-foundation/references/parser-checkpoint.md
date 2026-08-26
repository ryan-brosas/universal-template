<!-- capsule-v2 -->
# Zero-cost release-mode checkpoints — what does a parser checkpoint actually snapshot, and why is the release build's empty?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How can `checkpoint()/rewind()` be cheap enough to call speculatively on every ambiguous production, and what guarantees correctness when it snapshots nothing?

## JsParserStateCheckpoint (debug-assertions-only state plane)
**Path/Symbol:** `crates/biome_js_parser/src/state.rs:JsParserStateCheckpoint` (:212-241) + `JsDebugParserStateCheckpoint` (:247-282).
**Signature:** `struct JsParserStateCheckpoint { #[cfg(debug_assertions)] debug_checkpoint: JsDebugParserStateCheckpoint }`; `fn rewind(self, state: &mut JsParserState)` — note self by value, single-use.
**Data Shape:** Release (`#[cfg(not(debug_assertions))]`) the checkpoint struct is a zero-sized unit and both `snapshot`/`rewind` are no-ops. Debug builds store `parsing_context`, `label_set_len`, `strict`, `default_item`, `duplicate_binding_parent`, `name_map_len`.

### Decisive source
```rust
// Most of the [JsParserState] is scoped state. It should, therefore, not be necessary to rewind
// that state because that's already taken care of by `with_state` and `with_scoped_state`.
// But, you can never no and better be safe than sorry...
fn rewind(self, state: &mut JsParserState) {
    assert_eq!(state.parsing_context, self.parsing_context);
    assert_eq!(state.label_set.len(), self.label_set_len);
    assert_eq!(state.strict, self.strict);
    // ...
}
```

**Flow:** `JsParser::checkpoint()` captures three planes: `context.checkpoint()` (event-stack length), `source.checkpoint()` (lexer buffer + trivia length), `state.checkpoint()` → speculative code runs → `rewind()` truncates events/trivia and *asserts* (not restores) that scoped state returned to its old value.
**Invariant:** Scoped state must be restored by the `with_state` machinery alone; the checkpoint deliberately refuses to duplicate that work in release builds. If a production mutates scoped state and relies on `rewind` to undo it, release builds silently corrupt sibling parses — the debug assertion exists precisely to catch this in CI.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/paren_or_arrow_expr.js` + `error/paren_or_arrow_expr_invalid_params.js` (speculative arrow parses rewind constantly; any scoped-state leak would misparse the following statements).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "JsParserCheckpoint rewind with_state", limit: 10, fields: ["signature", "name", "file"] });
```
Resolves `parser.JsParser.with_state` (110-119), `state.JsParserStateCheckpoint.rewind` (:240).

## Verdict
Adopt the split: real restore for scoped state via guards, zero-cost assert-only checkpoints for whole-parser rewinds, gated behind debug assertions; adapt the asserted field list to your state shape; omit Biome's exact cfg names. A porter who "fixes" the empty release checkpoint by snapshotting everything reintroduces the per-token cost the design removes.
