<!-- capsule-v2 -->
# Cow-to-token text bridge — how does replaced token text stay verifiable against the CST and source-map-mappable at once?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** when a formatter substitutes cleaned literal content for a token, how does the printer know which output bytes still correspond to WHICH source positions — and how is the borrowed fast path kept honest?

## SyntaxTokenCowSlice
**Path/Symbol:** `crates/biome_formatter/src/builders.rs` — `syntax_token_cow_slice` (:404-412), `SyntaxTokenCowSlice::fmt_segment` (:443-480), `Text` mapped arm (:380-388), `with_literal_line_breaks` wrapper (:438+). Consumers: JS number path `crates/biome_js_formatter/src/trivia.rs:46-70` (`format_number_token` → `format_replaced` + `syntax_token_cow_slice(..., token.text_trimmed_range().start())`), string path `crates/biome_js_formatter/src/utils/string_utils.rs:84-94`.
**Signature:** `pub fn syntax_token_cow_slice<'a, L: Language>(text: Cow<'a, str>, token: &'a SyntaxToken<L>, start: TextSize) -> SyntaxTokenCowSlice<'a, L>`; segment fmt writes `FormatElement::{LocatedTokenText, MappedLocatedTokenText, Text, MappedText}`.
**Data Shape:** `Cow` polarity IS the protocol: `Borrowed` ⇒ text is a byte-identical slice of the token (source-position-preserving); `Owned` ⇒ content was rewritten (number trimming / quote normalization), positions map from the START offset only. `start: TextSize` = absolute source offset of the replaced span (callers pass `token.text_trimmed_range().start()`).

### Decisive source
```rust
// builders.rs:409 — entry gate: only LF may terminate lines inside replaced text:
debug_assert_normalized_newlines(&text);

// :455-462 — the borrowed fast path is PROVEN, not assumed:
match &self.text {
    Cow::Borrowed(_) => {
        let range = TextRange::at(start, text.text_len());
        debug_assert_eq!(
            text,
            &self.token.text()[range - self.token.text_range().start()],
            "The borrowed string doesn't match the specified token substring. Does the borrowed string belong to this token and range?"
        );
        ...
        f.write_element(FormatElement::MappedLocatedTokenText { slice, source_position: start }) // or LocatedTokenText
    }
```
**Flow:** construct with (cow, owning token, absolute start). Borrowed arm asserts byte-identity against the token slice then emits located/mapped LOCATED elements so source maps stay exact. Owned arm emits plain `Text`, upgrading to `MappedText { text, source_position }` when source-map generation is enabled. `with_literal_line_breaks` splits embedded `\n` into non-propagating literal lines that reset indentation to document root (multi-line raw strings).
**Invariant:** the debug_assert on the borrowed path is the whole honesty contract — if you ever hand this builder a borrowed string that isn't truly a slice of the token, tests fail loudly instead of silently mis-mapping source positions; a porter who drops the assert loses the only guard that Cow polarity matches reality. Newlines inside replaced text must be LF-normalized upstream (`normalize_newlines`) or the assert fires.
**Probe:** consumers pin both polarities end-to-end through real formatter snapshots: number trimming `crates/biome_js_formatter/tests/specs/js/module/number/literal.js(+snap)` and its CSS twin `crates/biome_css_formatter/tests/specs/css/numbers/numbers.css`; string re-quoting under `crates/biome_js_formatter/tests/specs/js/module/string/`. Greps: `grep -nF "debug_assert_normalized_newlines(&text)" crates/biome_formatter/src/builders.rs` → :409; `grep -nF 'The borrowed string doesn' t match' …` (single-token form `'borrowed string doesn'`) → :457; `grep -c 'MappedText\|LocatedTokenText' crates/biome_formatter/src/builders.rs` ≥ 4; `grep -nF 'fn format_number_token' crates/biome_js_formatter/src/trivia.rs` → :46.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"syntax_token_cow_slice"}'
# biome.crates.biome_formatter.src.builders syntax_token_cow_slice Function 404-412
```

## Verdict
Adopt the Cow-polarity bridge + debug-proven borrowed path for any token-text substitution; adapt element kinds to your IR's located-text vocabulary; omit `with_literal_line_breaks` unless your printer supports non-propagating literal lines. Coverage: file indexed clean (`no_recorded_issue` @ 2026-08-16T00:20:04Z); snapshot suites are snapshot-pinned (no unit assertions beyond the debug gate).
