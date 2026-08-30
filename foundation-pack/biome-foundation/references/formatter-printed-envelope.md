<!-- capsule-v2 -->
# Printed result envelope — how does a formatter hand back code, source positions, and verbatim ranges in ONE value that stays correct for range formatting and trailing-newline suppression?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** what are the exact post-print steps (source-map application, newline stripping, sourcemap/verbatim ownership) and the marker semantics every consumer must know?

## The print → map_printed → strip chain
**Path/Symbol:** `crates/biome_formatter/src/lib.rs` — `Formatted::print` (:1153-1171) and `print_with_indent(indent, SourceMapGeneration)` (:1173-1207, threads generation into PrinterOptions); both run the SAME three steps. `Printed { code, range: Option<TextRange>, sourcemap: Vec<SourceMarker>, verbatim_ranges }` (:1209-1216) with accessors incl. `take_sourcemap`/`take_verbatim_ranges` (`std::mem::take`, :1265-1284), `verbatim()` iterator yielding `(TextRange, &str)` slices, `strip_trailing_newlines` (:1295-1306, pops ALL trailing `\n`/`\r` chars). `SourceMarker { source: TextSize, dest: TextSize }` (:1070-1075) with the doc-pinned caveat "It's not guaranteed that the markers are sorted by source position" (:1242-1244 — line-suffix comments reorder them).
**Signature:** `pub fn print(&self) -> PrintResult<Printed>` where the context supplies BOTH print options and `Option<&TransformSourceMap>`.
**Data Shape:** `range = None` means whole-file coverage; `Some(range)` (set by format_range/format_sub_tree) marks the input span this output replaces. Verbatim ranges index INTO `code` (output coordinates, not source).

### Decisive source
```rust
// lib.rs:1155-1169 — order is load-bearing: print → remap → strip:
let printed = Printer::new(print_options).print(&self.document)?;
let printed = match self.context.source_map() {
    Some(source_map) => source_map.map_printed(printed),
    None => printed,
};
// Strip trailing newlines if the option is set to false
let printed = if !self.context.options().trailing_newline().value() {
    printed.strip_trailing_newlines()
} else {
    printed
};
```
```rust
// lib.rs:2515-2538 — direct test pins borrowed-slice markers as IDENTITY pairs:
assert_eq!(printed.as_code(), "ab\ncd");
assert_eq!(printed.sourcemap(), [
    SourceMarker { source: 0.into(), dest: 0.into() },
    SourceMarker { source: 2.into(), dest: 2.into() }, ...
]);
```
**Flow:** printer emits markers in TRANSFORMED-tree coordinates; when a pre-process ran, `map_printed` re-bases each marker's `source` through deleted ranges BEFORE anything else consumes them (see formatter-transform-sourcemap-kernel for the out-of-order marker handling). Trailing-newline stripping happens LAST so a `range`-carrying Printed still ends exactly at the sliced output; `strip_trailing_newlines` handles LF/CRLF/CR uniformly (six-case test :2956-2987). Range consumers then slice via markers with the equal-dest tie-break (formatter-range-kernel). Ownership: `take_sourcemap`/`take_verbatim_ranges` let callers move the Vecs out without cloning before discarding code.
**Invariant:** applying `TransformSourceMap::map_printed` AFTER slicing or stripping would mis-map — the chain order (print → map → strip → slice) must be preserved by any port. Marker unsortedness is contractual: any consumer sorting them must keep the (source,dest) pairing intact.
**Probe:** `grep -n 'pub fn print(' crates/biome_formatter/src/lib.rs` → 1 hit :1153; `sed -n '1155,1157p' …` shows `Printer::new(print_options).print(&self.document)?`; `grep -n 'fn strip_trailing_newlines' …` → :1295; direct tests: `test_strip_trailing_newlines` :2956 (LF/CRLF/CR/multi/middle/empty), `borrowed_syntax_token_slice_preserves_literal_lines_and_source_markers` :2515 + owned variant :2560 (source-offset shift) + `syntax_token_slice_trailing_literal_lines_advance_source_for_generated_text` :2604 (trailing literal line ADVANCES the pending source position for generated text).
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"SourceMarker"}'
# SourceMarker Struct lib.rs:1070-1075
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"format_node_with_source_map_generation"}'
# entry pipeline feeding Formatted::print
```

## Verdict
Adopt the print→map→strip ordering and the four-field envelope verbatim; adapt accessor set to your host (keep a take-style move-out for large maps); omit `verbatim_ranges` only if you never print nodes verbatim. Coverage: lib.rs partial only inside tests; production ranges fully indexed @ generation 2026-08-16T00:20:04Z.
