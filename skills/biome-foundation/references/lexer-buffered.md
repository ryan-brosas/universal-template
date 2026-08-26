<!-- capsule-v2 -->
# Buffered lexer with lookahead — how do you give a single-token lexer cheap Nth-token lookahead without re-lexing?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome` (full mode, 141,682 nodes / 644,530 edges, generation 2026-08-16). **Question:** the `Lexer` trait only exposes the current token and `next_token`; how does `BufferedLexer` add `nth`/`nth_non_trivia` lookahead while keeping every token lexed at most once, and how do re-lex/context switches invalidate the cache?

## The buffered-lookahead seam
**Path/Symbol:** `crates/biome_parser/src/lexer.rs` — `Lexer` trait (12-347), `ReLexer` (349-353), `LexerWithCheckpoint` (355-359), `BufferedLexer` (395-725), `Lookahead` (424-495), `LookaheadIterator` (771-825), `LookaheadToken` (828-851), `LexerCheckpoint` (866-894), `TokenFlags` (896-943).
**Signature:** `BufferedLexer::next_token(context) -> Kind`; `nth_non_trivia(&mut self, n) -> Option<LookaheadToken>`; `current()/current_range()/has_preceding_line_break()`; `re_lex(context)`; `force_relex_in_context(context)`; `force_relex_at_line_start(context)`; `rewind(checkpoint)`; `lookahead_iter() -> LookaheadIterator`.
**Data Shape:** `BufferedLexer{ lookahead: Lookahead, current: Option<LexerCheckpoint>, inner: Lex }`. `Lookahead{ all_checkpoints: VecDeque<LexerCheckpoint>, non_trivia_checkpoints: VecDeque<LexerCheckpoint> }`. `LexerCheckpoint{ position, current_start, current_kind, current_flags: TokenFlags, after_line_break, after_whitespace, unicode_bom_length, diagnostics_pos: u32 }`. `TokenFlags` is a u8 bitflags (PrecedingLineBreak=1<<0, UnicodeEscape=1<<1, PrecedingWhitespace=1<<2).

### Decisive source
```rust
// lexer.rs:519-545 — next_token: reset lookahead on non-regular context, else pop cache
pub fn next_token(&mut self, context: Lex::LexContext) -> Lex::Kind {
    if !context.is_regular() {
        self.reset_lookahead();          // context switch => cached tokens may differ
    } else if let Some(next) = self.lookahead.pop_front() {
        let kind = next.current_kind;
        if self.lookahead.is_empty() { self.current = None; }
        else { self.current = Some(next); }
        return kind;
    }
    self.current = None;
    self.inner.next_token(context)
}
```
`nth_non_trivia(n)` (732-759) first checks `non_trivia_checkpoints[n-1]`, else resumes from `remaining = n - non_trivia_len()` by iterating `lookahead_iter().skip(all_len())` — so repeated lookahead never re-lexes. `LookaheadIterator::next` (789-822) caches each lexed checkpoint into `all_checkpoints` (and `non_trivia_checkpoints` if not trivia) and stores the pre-lookahead inner state into `self.current` so `BufferedLexer::current()` stays put while the inner lexer runs ahead. `reset_lookahead`/`re_lex`/`force_relex_in_context` rewind the inner lexer to the current token's START (neutral `EOF` kind, empty flags) and clear the cache, because a re-lexed token can change every following token.
**Flow:** parser calls `p.nth(2)` → `NthToken::nth` (token_source.rs:133-181) → `BufferedLexer::nth_non_trivia(2)` → fills lookahead cache by lexing forward, returning `LookaheadToken` (kind/range/line-break/whitespace flags). The inner lexer's `current` is now 2 tokens ahead, but `BufferedLexer::current` still reports the pre-lookahead token. On the next `next_token`, the cached checkpoints are popped in order — no re-lexing. Context changes (e.g. JS template → expression) call `force_relex_in_context` to rewind to token start and re-lex fresh.
**Invariant:** every token is lexed at most once in a given regular context (the cache is the single source of truth); a non-regular context, re-lex, or rewind MUST clear the lookahead cache or stale kinds leak; `nth_non_trivia` asserts `n != 0` and returns `None` past EOF (caller maps to `EOF` kind).
**Probe:** `crates/biome_js_parser/src/parser.rs:JsParser::lookahead` (86-95) is the main consumer; `crates/biome_js_parser/tests/spec_test.rs` snapshot corpus exercises lookahead-driven disambiguation (e.g. `(a,b,c)...` arrow-vs-paren). No direct unit test of `BufferedLexer`; `token_set.rs` has the only `#[test]`s in the crate.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "BufferedLexer nth_non_trivia lookahead reset_lookahead", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-deque (all + non-trivia) checkpoint cache, the "cache is truth / clear on context change" invariant, and the rewind-to-token-start re-lex pattern; adapt `TokenFlags` and `LexContext` to host token kinds; omit the grit `µ` metavariable handling (CSS/JS-specific). Coverage caveat: no direct unit test — behavior pinned by the JS parser snapshot corpus and `JsParser::lookahead`.
