<!-- capsule-v2 -->
# Two-phase embedded formatting — how do you format <script>/<style> content with a DIFFERENT language formatter after the host document's IR already exists?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** embedded languages need a second formatter pass over ranges the first pass skipped — what is the tag protocol that keeps token-tracking assertions satisfied across both phases?

## StartEmbedded/EndEmbedded placeholder protocol
**Path/Symbol:** `crates/biome_formatter/src/lib.rs` — `Formatted::format_embedded` (:1095-1128, the resolver), `Formatted::propagate_expand` (:1130-1134, MUST run AFTER format_embedded); `print()`/`print_with_indent` (:1153-1207, source-map application then trailing-newline strip). Producer side: `crates/biome_html_formatter/src/html/auxiliary/element.rs` `fmt_node` (emits the tag pair; `embedded_node_range` hook returns None by default) and `crates/biome_html_formatter/src/lib.rs:238` StartEmbedded match arm. Consumer side: `crates/biome_service/src/file_handlers/javascript.rs` `format_embedded` (:1590-, snippet FxHashMap keyed by range :1605-1608, callback closure :1611 wrapping documents in Hard line + StartIndent tags).
**Signature:** `pub fn format_embedded<F>(&mut self, mut fn_format_embedded: F) where F: FnMut(TextRange) -> Option<Document>`.
**Data Shape:** phase 1 emits `Tag(StartEmbedded(range)) … Tag(EndEmbedded)` pairs with NO content between; tokens inside those nodes are PRE-tracked via `state.track_token(&token)` in the same pass so debug token coverage stays complete. Phase 2 replaces each resolved pair with an `Interned` document.

### Decisive source
```rust
// lib.rs:1100-1119 — pairing is preserved even when resolution FAILS:
let mut last_start_resolved = false;
self.document.transform(move |element| match element {
    FormatElement::Tag(Tag::StartEmbedded(range)) => match fn_format_embedded(*range) {
        Some(document) => {
            last_start_resolved = true;
            Some(FormatElement::Interned(Interned::new(document.into_elements())))
        }
        None => {
            // Keep the StartEmbedded tag so it stays paired with EndEmbedded.
            last_start_resolved = false;
            None
        }
    },
    FormatElement::Tag(Tag::EndEmbedded) => {
        if last_start_resolved { Some(FormatElement::Line(LineMode::Hard)) }
        else {
            // Keep EndEmbedded paired with the unresolved StartEmbedded.
            None
        }
    }
    _ => None,
});
```
**Flow:** (1) HTML/JSX-ish host formatter detects embeddable nodes via `embedded_node_range`, pre-tracks their tokens, writes the empty tag pair. (2) Service layer parses those ranges with the embedded language's parser and calls `formatted.format_embedded(closure)`; the closure maps range → sub-formatter Document or None. (3) Resolved pairs become interned element runs followed by a Hard line; unresolved pairs stay untouched so the document remains well-formed. (4) `propagate_expand()` then fixes group-expansion flags ACROSS the newly inserted content — running it before format_embedded would miss groups inside embedded documents. (5) Normal print path applies context source map + strips trailing newlines when `TrailingNewline(false)` (`strip_trailing_newlines` pops ALL trailing `\n`/`\r` :1295-1303).
**Invariant:** the `last_start_resolved` flag is what prevents orphan tags under partial resolution — a porter who drops BOTH tags on failure corrupts pairing; one who drops only the content leaves an empty pair that prints as nothing but still satisfies pairing. Token pre-tracking is equally load-bearing: without it `assert_formatted_all_tokens` panics in debug for every embedded node.
**Probe:** `grep -n 'fn format_embedded' crates/biome_formatter/src/lib.rs` → 1 hit :1095; `grep -c 'last_start_resolved' crates/biome_formatter/src/lib.rs` → 4; `grep -c 'StartEmbedded' crates/biome_html_formatter/src/lib.rs` → 2; `grep -n 'state.track_token(&token)' crates/biome_html_formatter/src/lib.rs` → :234; consumer wiring `grep -n 'formatted.format_embedded(move |range|' crates/biome_service/src/file_handlers/javascript.rs` → :1611. Graph note: name_pattern `StartEmbedded` total:0 (tag variants are enum values, not indexed symbols) — retrieve via BM25 query "StartEmbedded EndEmbedded embedded formatting tags" which ranks FormatHtmlEmbeddedContent.embedded_node_range (html/auxiliary/embedded_content.rs 11-29) rank#1.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"StartEmbedded EndEmbedded embedded formatting tags","limit":6}'
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"format_node_with_source_map_generation"}'
```

## Verdict
Adopt the two-phase protocol for any host-with-embeds formatter; adapt the closure's range→Document mapping to your per-language dispatch; omit the Interned wrapper only if your IR lacks cheap cloning (then re-walk elements instead). Coverage: all three cited planes no_recorded_issue @ generation 2026-08-16T00:20:04Z.
