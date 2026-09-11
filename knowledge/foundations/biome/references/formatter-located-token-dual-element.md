<!-- capsule-v2 -->
# Located token text dual emission — why does the SAME builder produce two different FormatElements depending on source-map generation?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** A porter slicing a syntax token (e.g. for range formatting or verbatim printing) must pick the right element — what does `located_token_text` emit under each mode and what precondition does it debug-assert?

## located_token_text → MappedLocatedTokenText vs LocatedTokenText
**Path/Symbol:** `crates/biome_formatter/src/builders.rs:573-586` (`located_token_text`), `builders.rs:588-610` (`LocatedTokenText` struct + dual-mode `Format::fmt`), `builders.rs:618-623` (`debug_assert_normalized_newlines`).
**Signature:** `pub fn located_token_text<L: Language>(token: &SyntaxToken<L>, range: TextRange) -> LocatedTokenText`; fmt arms on `f.source_map_generation().is_enabled()`.
**Data Shape:** slice = `token.token_text().slice(range - token.text_range().start())` (relative range); `source_position: TextSize` rides along; the disabled arm computes `TextWidth::from_text(&self.text, f.options().indent_width())` (tab-aware width).

### Decisive source
```rust
// builders.rs:597-609
fn fmt(&self, f: &mut Formatter<Context>) -> FormatResult<()> {
    if f.source_map_generation().is_enabled() {
        f.write_element(FormatElement::MappedLocatedTokenText {
            slice: self.text.clone(),
            source_position: self.source_position,
        })
    } else {
        f.write_element(FormatElement::LocatedTokenText {
            slice: self.text.clone(),
            text_width: TextWidth::from_text(&self.text, f.options().indent_width()),
        })
    }
}
// builders.rs:618-623
fn debug_assert_normalized_newlines(text: &str) {
    debug_assert!(
        !text.contains('\r'),
        "The content '{text}' contains a carriage return, but formatter text must use LF line endings. \
         Normalize source text with `normalize_newlines` before constructing formatter text."
    );
}
```

**Flow:** caller slices a token with an absolute source range → constructor relativizes against the token start and asserts LF-normalized text → at format time the element chosen depends on the SESSION's source-map setting: enabled ⇒ `MappedLocatedTokenText` (carries source offset so the printer can emit markers); disabled ⇒ plain `LocatedTokenText` (carries precomputed tab-aware width for fits measurement).
**Invariants:** (1) Input text MUST be LF-normalized BEFORE slicing — `\r` anywhere trips a debug_assert in debug builds and silently misprints widths in release; normalize via `normalize_newlines` upstream. (2) The two elements are NOT interchangeable: dropping the mapped variant loses sourcemap fidelity; dropping width precomputation breaks fits measurement. (3) The same dual-emission pattern recurs in this file for every source-anchored builder (`Mapped*` family :391/:471/:484) — port it as one policy decision, not per-call-site.
**Probe:** `grep -c 'is_disabled()' crates/biome_formatter/src/builders.rs` → `1` (source_position guard shares the gate); `grep -c 'MappedLocatedTokenText {' crates/biome_formatter/src/builders.rs` → `2` (this site + one sibling); `grep -n 'TextWidth::from_text' crates/biome_formatter/src/builders.rs` → 4 hits incl. `606:`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"LocatedTokenText source position","limit":5,"detail":"ids"}'
```
Resolves `LocatedTokenText Struct 588-591`, `.fmt Method 613-615` line-exact.

## Verdict
Adopt the generation-gated dual element and the LF-precondition assert; adapt TextWidth computation to host width semantics (tab handling must match). Direct-test caveat: behavior is exercised indirectly through range-formatting snapshot tests (`test_range_formatting*` in biome_js_formatter/src/lib.rs tests) rather than a unit test on this builder.
