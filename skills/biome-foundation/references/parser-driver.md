<!-- capsule-v2 -->
# Event-stream parser driver — how do you drive a parser as a flat event list that a sink rebuilds into a lossless tree?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome` (full mode, 141,682 nodes / 644,530 edges, generation 2026-08-16). **Question:** the parser core never builds nodes directly — it emits a flat `Event` stream that `process` folds into a `TreeSink`. What is that contract, and how do Marker/CompletedMarker/checkpoints make speculative + forward-parented parsing safe?

## The event-stream seam
**Path/Symbol:** `crates/biome_parser/src/event.rs:process` (48-104); `crates/biome_parser/src/marker.rs:Marker/CompletedMarker` (full); `crates/biome_parser/src/lib.rs:ParserContext/ParserContextCheckpoint/Parser` (39-573).
**Signature:** `pub fn process<K: SyntaxKind + PartialEq>(sink: &mut impl TreeSink<Kind=K>, mut events: Vec<Event<K>>, errors: Vec<ParseDiagnostic>)`; `Parser::start() -> Marker`; `Marker::complete(p, kind) -> CompletedMarker`; `CompletedMarker::precede(p) -> Marker`; `ParserContext::checkpoint() -> ParserContextCheckpoint` / `rewind(checkpoint)`.
**Data Shape:** `Event<K>` is exactly three variants — `Start{kind, forward_parent: Option<NonZeroU32>}`, `Finish`, `Token{kind, end: TextSize}`. `ParserContext` holds `events: Vec<Event>`, `skipping: bool`, `diagnostics: Vec<ParseDiagnostic>`. A `Marker` records `pos` (index into events), `start: TextSize`, and a `DebugDropBomb` forcing complete/abandon.

### Decisive source
```rust
// event.rs:48-104 — fold events into the sink, resolving forward_parent chains
pub fn process<K>(sink: &mut impl TreeSink<Kind=K>, mut events: Vec<Event<K>>, errors: Vec<ParseDiagnostic>) {
    sink.errors(errors);
    let mut forward_parents = Vec::new();
    for i in 0..events.len() {
        match &mut events[i] {
            Event::Start { kind, forward_parent, .. } => {
                if *kind == K::TOMBSTONE { continue; }
                forward_parents.push(*kind);
                let mut idx = i; let mut fp = *forward_parent;
                while let Some(fwd) = fp {
                    idx += u32::from(fwd) as usize;
                    fp = match mem::replace(&mut events[idx], Event::tombstone()) {
                        Event::Start { kind, forward_parent, .. } => {
                            if kind != K::TOMBSTONE { forward_parents.push(kind); }
                            forward_parent
                        }
                        _ => unreachable!(),
                    };
                }
                for kind in forward_parents.drain(..).rev() { sink.start_node(kind); }
            }
            Event::Finish => sink.finish_node(),
            Event::Token { kind, end } => sink.token(*kind, *end),
        }
    }
}
```
`Marker::complete` writes the kind into the already-pushed `Start` slot then pushes a `Finish`; `Marker::abandon` pops the trailing tombstone `Start` (asserting kind==TOMBSTONE) so children attach to the parent. `CompletedMarker::precede` inserts a NEW `Start` after the completed node and sets the OLD node's `forward_parent` to the relative distance (`NonZeroU32::try_from(new_pos.pos - self.start_pos)`), so a node completed before its parent is discovered can still become its child. `undo_completion` flips both the `Start` and `Finish` to TOMBSTONE and returns a fresh `Marker` for re-parse.

**Flow:** `Parser::start()` pushes a tombstone `Start` and returns a `Marker` → grammar consumes tokens via `bump`/`eat`/`expect` (each pushes a `Token{kind,end}` event) → `marker.complete(kind)` fills the kind and pushes `Finish` → on EOF, `ParserContext::finish()` yields `(events, diagnostics)` → `process` resolves forward_parents and drives the `TreeSink`. Speculative parsing snapshots with `checkpoint()` (event_pos + diagnostics_len) and restores with `rewind()` (drain events, truncate diagnostics) — the `ParserProgress` guard (`assert_progressing`) panics if a loop stops consuming, preventing infinite loops.
**Invariant:** the event list is append-only during parsing except `rewind`/`split_off_events` (both unsafe-marked); every `Start` must be `Finish`ed or `abandon`ed (DebugDropBomb panics otherwise); forward_parent distances are relative to the current index, so `process` must resolve them in one pass with `mem::replace` to TOMBSTONE (never re-read a consumed Start).
**Probe:** `crates/biome_js_parser/tests/spec_test.rs:run` (parse + `validate_eof_token` + snapshot AST/CST); `crates/biome_js_parser/src/rewrite.rs:rewrite_events` re-drives a sub-grammar through `process` after `split_off_events` — the real forward_parent/event-replay consumer. No direct unit test of `process` itself; behavior pinned by the whole js_test_suite snapshot corpus.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "CompletedMarker precede forward_parent event process", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the flat `Start/Finish/Token` event stream + `process` fold into a `TreeSink`, forward_parent for late-parent discovery, and checkpoint/rewind for speculative parsing; adapt the `TreeSink` trait and `Parser` trait methods to host kinds; omit the TOMBSTONE/`mem::replace` single-pass resolution only if you never need forward_parents (but keep it — it is what makes `precede` and re-parse safe). Coverage caveat: `process`/Marker have no dedicated unit test; correctness is enforced by the js_test_suite snapshot corpus and `rewrite_events`.
