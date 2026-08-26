<!-- capsule-v2 -->
# Parser trait surface — how do you expose bump/eat/expect, lookahead, and speculative-parse guards to grammar rules?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome` (full mode, 141,682 nodes / 644,530 edges, generation 2026-08-16). **Question:** grammar rules call a uniform set of token-consuming and lookahead helpers; what is the `Parser` trait contract, and how do `skipping`, `is_speculative_parsing`, and `SyntaxFeature` gate error behavior?

## The parser-API seam
**Path/Symbol:** `crates/biome_parser/src/lib.rs` — `Parser` trait (150-573), `ParserContext` (39-132), `ParserProgress` (576-615), `SyntaxFeature` (618-732), `AnyParse`/`NodeParse`/`EmbeddedNodeParse` (743-1044); `crates/biome_parser/src/token_source.rs` — `TokenSource`/`NthToken`/`BumpWithContext` (57-181).
**Signature:** `trait Parser { type Kind; type Source: TokenSource; fn context(&self); fn source(&self); fn cur()/cur_range()/cur_text(); fn at(kind)/at_ts(set); fn nth(n)/nth_at/nth_at_ts; fn bump(kind)/bump_any()/bump_remap(kind); fn eat(kind)->bool/eat_ts; fn expect(kind)->bool; fn start()->Marker; fn error(err); fn is_speculative_parsing()->bool }`.
**Data Shape:** `ParserContext{ events: Vec<Event>, skipping: bool, diagnostics: Vec<ParseDiagnostic> }`. `bump`/`eat`/`expect` all funnel through `do_bump` which pushes a `Token{kind,end}` event then either `bump()` or `skip_as_trivia()` depending on `context().skipping`.

### Decisive source
```rust
// lib.rs:390-400 — the single bump path (skipping turns the token into trivia)
fn do_bump(&mut self, kind: Self::Kind) {
    let end = self.cur_range().end();
    self.context_mut().push_token(kind, end);
    if self.context().skipping { self.source_mut().skip_as_trivia(); }
    else { self.source_mut().bump(); }
}
```
```rust
// lib.rs:494-506 — parse unsupported syntax as skipped trivia
fn parse_as_skipped_trivia_tokens<P: FnOnce(&mut Self)>(&mut self, parse: P) {
    let events_pos = self.context().events.len();
    self.context_mut().skipping = true;
    parse(self);
    self.context_mut().skipping = false;
    self.context_mut().events.truncate(events_pos);   // drop any start/finish events
}
```
`bump(kind)` asserts the current token equals `kind` (with a text+range panic message); `bump_any` asserts `!= EOF`; `eat` returns bool without error; `expect` calls `eat` then `error(expected_token(kind))` on failure. `error` dedupes diagnostics sharing the same start offset. `is_speculative_parsing()` defaults false and disables "more involved error recovery" (see parse_recovery.md). `SyntaxFeature::exclusive_syntax`/`parse_exclusive_syntax`/`parse_supported_syntax`/`excluding_syntax` gate a parse behind a feature flag, adding a diagnostic and changing the node to `bogus` when unsupported (`parse_exclusive_syntax` truncates diagnostics produced during the gated parse before re-adding its own). `AnyParse` is the language-neutral parse result (Node vs EmbeddedNode) with `into_language_root`/`syntax`/`tree`/`has_errors` and panic-guarded accessors.
**Flow:** grammar rules consume tokens via `bump`/`eat`/`expect` (each pushing an event and advancing the token source) → optional lookahead via `nth`/`nth_at` → `start()`/`complete()` build nodes → errors via `error`/`err_builder` → `ParserContext::finish()` yields events+diagnostics → `process` builds the tree. `skipping` mode lets a rule swallow unsupported syntax as trivia without tree nodes.
**Invariant:** `bump`/`bump_any` must never consume EOF (asserted); `expect` must always emit a diagnostic on failure; `skipping` mode must truncate events on exit so swallowed syntax leaves no tree residue; speculative parsing must not perform error recovery.
**Probe:** `crates/biome_js_parser/tests/spec_test.rs` drives the full `JsParser`; `crates/biome_js_parser/src/rewrite.rs:rewrite_events` uses `split_off_events` + `process` to re-shape a sub-grammar. No direct unit test of the `Parser` trait.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "Parser bump_any parse_as_skipped_trivia_tokens SyntaxFeature exclusive_syntax", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the uniform bump/eat/expect surface, the skipping-as-trivia escape hatch, the diagnostic dedup, and the `SyntaxFeature` gating (diagnostic + to_bogus); adapt kinds and feature flags per grammar; omit `AnyParse`'s embedded-node machinery unless you parse embedded content. Coverage caveat: no dedicated unit test — pinned by the js_test_suite corpus + `rewrite_events`.
