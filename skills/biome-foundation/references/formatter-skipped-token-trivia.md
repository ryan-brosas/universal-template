<!-- capsule-v2 -->
# Skipped-trivia verbatim reconstruction — how is unparsable source (regex, private names) reprinted byte-stable with its comments?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** when the lexer emits skipped trivia for constructs the formatter cannot re-print, what protocol reprints them verbatim — and which separator decisions keep surrounding whitespace faithful?

## The skipped seam
**Path/Symbol:** `crates/biome_formatter/src/trivia.rs` — `FormatToken` trait (`format_removed/format_replaced/format_skipped_token_trivia`, :662-721), `FormatSkippedTokenTrivia::fmt_skipped` (:813-940), `FormatOnlyIfBreaks` (:724-786); registration side `builder.mark_has_skipped(&token)` + `Comments.has_skipped`.
**Signature:** `fn format_replaced(&self, token: &SyntaxToken<L>, content: &impl Format<C>, f) -> FormatResult<()>` — tracks the token as consumed, prints its skipped trivia, THEN the replacement.
**Data Shape:** scan state `(lines, spaces)` reset at every comment/skipped piece; collected `dangling_comments: Vec<SourceComment>` (pre-marked formatted=true); `skipped_range: Option<TextRange>` covering first→last skipped piece; output wrapped in `Tag::StartVerbatim(VerbatimKind::Verbatim { length }) … EndVerbatim`.

### Decisive source
```rust
// trivia.rs:876-889 — before the FIRST skipped piece, reproduce whatever
// separated it from the previous token; between later pieces use the
// accumulated lines/spaces. This is where "no space in source ⇒ no space out"
// is enforced rather than assumed:
if dangling_comments.is_empty() {
    match lines {
        0 if spaces == 0 => { /* keep it glued */ }
        0 => write!(f, [space()])?,
        _ => write!(f, [hard_line_break()])?,
    };
} else {
    match lines {
        0 => write!(f, [space()])?,
        1 => write!(f, [hard_line_break()])?,
        _ => write!(f, [empty_line()])?,
    };
}
```
**Flow:** count trailing whitespace/newlines of prev_token in REVERSE (so spaces after the last newline are counted, :822-840); walk leading pieces — whitespace accumulates `spaces`, newlines accumulate `lines` and zero spaces, comments buffer into `dangling_comments` (resetting counters), each SKIPPED piece flushes pending separators then extends `skipped_range` and clears buffered comments; finally print located verbatim text over the range inside Start/EndVerbatim tags and close with a trailing separator ladder (none/space/hard-break by lines+spaces; with dangling comments, their own lines decide). Consumers must call one of the trait methods — `format_removed` keeps ONLY skipped trivia (token itself dropped), `format_replaced` swaps content under it.
**Invariant:** verbatim output must be wrapped in Verbatim tags or range-formatting/source-maps lose track of it, and the token MUST be registered via `track_token`/`mark_has_skipped` exactly once — double-processing duplicates trivia. Porters who normalize separators here break idempotence on files containing regexes (`/ /` with embedded spaces is the canonical case).
**Probe:** consumer sites pin the contract — `crates/biome_js_formatter/src/lib.rs` (format_skipped wiring), `crates/biome_js_formatter/src/syntax_rewriter.rs`; `crates/biome_json_formatter/src` uses the same API for JSONC extensions. No dedicated biome_formatter unit test exists for fmt_skipped (covered transitively by js/json formatter suites that include regex literals); recorded as an honesty note.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "FormatSkippedTokenTrivia fmt_skipped format_replaced", limit: 10, fields: ["signature", "name", "file"] });
// FormatSkippedTokenTrivia::fmt_skipped trivia.rs 815-940 (line-exact)
```

## Verdict
Adopt the track-once + verbatim-tag + separator-ladder trio for any lossless formatter with unparsable tokens; adapt to your trivia model; omit `FormatOnlyIfBreaks` unless you need break-conditional token retention. Coverage caveat: no direct unit test in this crate — pinned transitively through language-formatter suites.
