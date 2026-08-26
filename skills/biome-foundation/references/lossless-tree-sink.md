<!-- capsule-v2 -->
# Lossless tree sink — how do you attach leading/trailing trivia to tokens while rebuilding a tree from events, and auto-append an EOF token?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome` (full mode, 141,682 nodes / 644,530 edges, generation 2026-08-16). **Question:** `process` hands a `TreeSink` a stream of start/finish/token calls; how does `LosslessTreeSink` decide which trivia pieces are a token's leading vs trailing trivia, and how does it guarantee an EOF token exists?

## The trivia-attachment seam
**Path/Symbol:** `crates/biome_parser/src/tree_sink.rs` — `TreeSink` trait (9-24), `LosslessTreeSink` (30-168), `OffsetLosslessTreeSink` (176-244); `crates/biome_parser/src/token_source.rs:Trivia` (7-55).
**Signature:** `LosslessTreeSink::new(text, trivia) -> Self` / `with_cache(text, trivia, &mut NodeCache)`; `impl TreeSink { token(kind,end), start_node(kind), finish_node(), errors(errs) }`; `finish(self) -> (SyntaxNode<L>, Vec<ParseDiagnostic>)`.
**Data Shape:** `LosslessTreeSink{ text: &'a str, trivia_list: &'a [Trivia], text_pos: TextSize, trivia_pos: usize, parents_count: usize, errors, inner: TreeBuilder, needs_eof: bool, trivia_pieces: Vec<TriviaPiece> }`. `Trivia{ kind: TriviaPieceKind, range: TextRange, trailing: bool }` (offset/len/end_offset accessors).

### Decisive source
```rust
// tree_sink.rs:122-167 — split trivia into leading (before token) vs trailing (after, before next linebreak)
fn do_token(&mut self, kind: L::Kind, token_end: TextSize) {
    if kind == L::Kind::EOF { self.needs_eof = false; }
    let token_start = self.text_pos;
    self.eat_trivia(false, token_end);          // leading trivia up to the token
    let trailing_start = self.trivia_pieces.len();
    self.text_pos = token_end;
    self.eat_trivia(true, token_end);           // trailing trivia until next linebreak
    let text = &self.text[TextRange::new(token_start, self.text_pos)];
    let leading = &self.trivia_pieces[0..trailing_start];
    let trailing = &self.trivia_pieces[trailing_start..];
    self.inner.token_with_trivia(kind, text, leading, trailing);
    self.trivia_pieces.clear();
}
fn eat_trivia(&mut self, trailing: bool, token_end: TextSize) {
    for trivia in &self.trivia_list[self.trivia_pos..] {
        if trailing != trivia.trailing() || self.text_pos != trivia.offset()
            || (!trailing && trivia.end_offset() > token_end) { break; }
        self.trivia_pieces.push(TriviaPiece::new(trivia.kind(), trivia.len()));
        self.text_pos += trivia.len(); self.trivia_pos += 1;
    }
}
```
`finish_node` (63-71): when `parents_count` drops to 0 and `needs_eof` is still true, it emits `do_token(EOF, text.len())` so every tree ends in an EOF token; `finish()` returns `(inner.finish(), errors)`. `OffsetLosslessTreeSink` wraps the inner sink and applies `base_offset` at `finish()` (via `SyntaxNodeWithOffset::new`), letting embedded content (JS in HTML) keep correct parent-document offsets — it forwards all four `TreeSink` methods unchanged and only adjusts on finish.
**Flow:** parser `process` calls `start_node`/`token`/`finish_node` → `do_token` consumes trivia pieces positioned before the token as leading, then (up to the next line break) as trailing → `token_with_trivia` builds the green token with both piece lists → on root finish, auto-EOF. The `text_pos`/`trivia_pos` cursors advance monotonically, so trivia is consumed exactly once.
**Invariant:** trivia is never stored as text in the tree — only `TriviaPiece(kind, len)` over the token's own buffer (see cst.md); the leading/trailing split is positional (offset == text_pos, and for leading also `end_offset <= token_end` to handle zero-length tokens); EOF is guaranteed present unless the parser explicitly emitted one.
**Probe:** `crates/biome_test_utils/src/lib.rs:validate_eof_token` (953) asserts the tree ends in EOF and is called by every `spec_test.rs` run; `has_bogus_nodes_or_empty_slots` (819) guards the lossless invariant. No direct unit test of the sink itself.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "LosslessTreeSink eat_trivia finish EOF token_with_trivia", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the positional leading/trailing trivia split, the auto-EOF-on-root-finish guarantee, and the offset wrapper for embedded content; adapt `Trivia`/`TriviaPiece` kinds to host; omit nothing core. Coverage caveat: sink behavior is pinned by `validate_eof_token` + the snapshot corpus, not a dedicated unit test.
