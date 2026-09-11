<!-- capsule-v2 -->
# Scoped parser state changes — how does a recursive-descent parser mutate context flags without leaking them into sibling productions?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How do you add parser state (strict mode, async/generator context, label set) that every production can consult but that reverts exactly at production exit?

## ChangeParserState trait + ParserStateGuard (state.rs / parser.rs)
**Path/Symbol:** `crates/biome_js_parser/src/state.rs:ChangeParserState` (:326-334), `ParserStateGuard` (:286-323), `crates/biome_js_parser/src/parser.rs:JsParser::with_state/with_scoped_state` (:99-119).
**Signature:** `trait ChangeParserState { type Snapshot: Default; fn apply(self, state: &mut JsParserState) -> Self::Snapshot; fn restore(state: &mut JsParserState, value: Self::Snapshot); }`
**Data Shape:** State = `ParsingContextFlags` (u8 bitflags), `label_set: IndexMap<String, LabelledItem>`, `strict: Option<StrictMode>`, plus unscoped accumulators (`name_map`, `default_item`, `duplicate_binding_parent`, `speculative_parsing`, `not_parenthesized_arrow`). Snapshot is whatever `apply` returns; restore takes it back.

### Decisive source
```rust
// parser.rs
#[inline]
pub(crate) fn with_state<C, F, R>(&mut self, change: C, func: F) -> R
where C: ChangeParserState, F: FnOnce(&mut JsParser) -> R {
    let snapshot = change.apply(self.state_mut());
    let result = func(self);
    C::restore(self.state_mut(), snapshot);
    result
}
```

**Flow:** caller builds a change struct (e.g. `EnterFunction(flags)`) → `with_state(change, body)` applies it, runs the production closure, restores on return → `with_scoped_state` variant wraps the same pair in an RAII `ParserStateGuard` whose `Drop` restores, so early returns and `?` still unwind correctly → `JsParser::checkpoint()/rewind()` compose all three planes (context events, token source, state).
**Invariant:** Every mutable field of `JsParserState` must be reachable through *some* `ChangeParserState` impl; a production that mutates state outside `with_state`/`with_scoped_state` leaks it to siblings. The generic blanket impl `ChangeParserStateFlags` (:513-528) snapshots by whole-field `mem::replace`, never per-bit patches — restoring writes the old field value back wholesale.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/function_in_single_statement_context_strict.js` (a function declared under `if (true)` in strict mode errors and becomes bogus — only observable because `StatementContext` and strict-mode state are restored around sibling statements).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "JsParserState EnterFunction FUNCTION_RESET_MASK", limit: 10, fields: ["signature", "name", "file"] });
```
Resolves `state.EnterFunction.apply` (579-588), `ParsingContextFlags::FUNCTION_RESET_MASK` (470-472).

## Verdict
Adopt the change/apply/restore trait + RAII guard as the universal pattern for scoped parse state; adapt the concrete flag sets to your language's spec parameters (`[+Yield]`, `[+Await]`, strict mode); omit Biome's debug-only checkpoint assertions if your host has no equivalent CI corpus. Coverage caveat: state.rs has no dedicated unit tests; behavior is pinned by the js_test_suite snapshot corpus.
