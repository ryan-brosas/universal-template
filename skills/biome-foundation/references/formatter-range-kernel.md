<!-- capsule-v2 -->
# Range-formatting kernel — how do you format a user selection inside a file without breaking the enclosing statement or mis-slicing the output?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** an editor sends (start,end) offsets — what is the full ladder that turns that range into a formatting root, an inferred indentation, and a correctly re-sliced Printed result?

## Root-selection + marker-slice ladder
**Path/Symbol:** `crates/biome_formatter/src/lib.rs` — `text_non_whitespace_range` (:1875-1906, trivia-piece scan keeping comments/skipped trivia); `format_range` (:1922-2185); Prettier parity note (:2030 "same algorithm as the findSiblingAncestors function in Prettier"); same-dest marker guard comments (:2083-2100); fallback defaults (:2152-2163); `format_sub_tree` (:2187-2252, initial-indent inference :2193-2244, forces `SourceMapGeneration::Enabled` at both build and print :2245-2248). Language hook: `is_range_formatting_node` (FormatLanguage trait :1694-1700; JS impl excludes JS_VARIABLE_DECLARATION so the whole STATEMENT formats — js_formatter/src/lib.rs:554-559, +1 after pass-15's `mod astro;` insert). Consumers: per-language `format_range` wrappers (json lib.rs:341, css lib.rs:402) and service handlers (javascript.rs:1518).
**Signature:** `pub fn format_range<Language: FormatLanguage>(root: &SyntaxNode<Language::SyntaxLanguage>, mut range: TextRange, language: Language) -> FormatResult<Printed>`.
**Data Shape:** input range may be empty (→ `Printed::new(String::new(), Some(range), …)`), out of bounds (→ `FormatError::RangeError { input, tree }`), or whitespace-padded. Output Printed carries the INPUT range actually overwritten (`Some(input_range)`), the sliced code, retained sourcemap markers and verbatim ranges.

### Decisive source
```rust
// lib.rs:2091-2097 (+ mirrored end-side 2129-2139) — equal-dest guard:
if prev_marker.dest == marker.dest {
    // we found a marker that is closer to the start range than we have
    // but we need to check if the marker has the same dest, otherwise we
    // can get an incorrect substring in the source text
    Some(prev_marker)   // keep the EARLIER source position
} else { Some(marker) }
```
```rust
// lib.rs:2152-2163 — no-marker fallbacks when range edges sit near file edges:
None => (common_root.text_range_with_trivia().start(), TextSize::from(0)),
// end side:
TextSize::try_from(printed.as_code().len()).expect("code length out of bounds"),
```
**Flow:** (1) token_at_offset for both edges; Between picks rightmost-left/leftmost-right; None falls back to first/last token; empty tree → `Printed::new_empty()`. (2) Trim range ends via `text_non_whitespace_range`, sliding onto neighbor tokens when an edge lands inside pure whitespace. (3) Climb ancestors from each edge token to the first `is_range_formatting_node`; if they differ, take the highest sibling pair via the take_while window, COVER their trimmed ranges, then find the lowest common ancestor by zipping reversed root paths. (4) `format_sub_tree(common_root, language)` — infers initial indent from the LAST whitespace trivia run before the root's first token (`Tab → count`, `Space → length / indent_width`, no whitespace → 0), prints with `SourceMapGeneration::Enabled` on BOTH sides. (5) Walk printed markers once: nearest `source <= range.start()` with the equal-dest tie-break, nearest `source >= range.end()` likewise; slice `printed.as_code()[output_range]` and return with `input_range`.
**Invariant:** the equal-dest rule is not an optimization — two markers sharing a dest (one element split/reordered in output) mean the LATER source offset would slice the wrong substring; the inline comment block documents the exact failure case. Indent inference is heuristic BY DESIGN ("may not actually match the current content of the file") — it uses configured indent style because there is no indentation detection.
**Probe:** `grep -n 'fn format_range<Language: FormatLanguage>' crates/biome_formatter/src/lib.rs` → 1 hit :1922; `grep -c 'text_non_whitespace_range' …` → 8 call sites; `grep -n 'findSiblingAncestors' …` → 1 hit :2030; `grep -n 'prev_marker.dest == marker.dest' …` → :2091+:2133; `grep -n 'IndentStyle::Tab => length,' …` → :2231 with `length / u16::from(width)` :2232; direct tests live on the consumer side (`crates/biome_js_formatter/src/lib.rs` range tests calling `format_range` :712/:746) plus `borrowed_syntax_token_slice_preserves_literal_lines_and_source_markers` :2515 pinning marker semantics used by the slicer.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"format_sub_tree"}'
# css/json/yaml formatter twins Function ~440/379/372 + core impl
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"format_range","limit":12}'
# consumer wrapper family across biome_service/file_handlers/*
```

## Verdict
Adopt the ladder verbatim for editor-integrated range formatting; adapt `is_range_formatting_node` predicates to your grammar's statement roots; omit the LCA sibling-window complexity only if your host always formats whole statements. This capsule executes pass-10 conditional #1's range-formatting half (the marker slicing was never cited before this pass). Coverage: lib.rs partial only inside tests; all cited consumer files no_recorded_issue.
