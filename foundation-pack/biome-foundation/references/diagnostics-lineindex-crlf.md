<!-- capsule-v2 -->
# Line-index CRLF dedup — how do you build a line-start offset table that never double-counts \r\n?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What is the correct byte-offset → line/column algorithm for text with mixed line endings?

## LineIndexBuf::from_source_text
**Path/Symbol:** `crates/biome_diagnostics/src/location.rs:LineIndexBuf::from_source_text` (:160-175), zero-copy `LineIndex` view (:128-146); consumer `display/frame.rs:SourceFile::new` (location computation).
**Signature:** `pub fn from_source_text(source: &str) -> Self` → `LineIndexBuf(Vec<TextSize>)` where TextSize = u32 byte offset; `LineIndex([TextSize])` is a `repr(transparent)` unsized view (transmute-d from `&[TextSize]`, SAFETY-commented :133-136).
**Data Shape:** entry 0 = 0 always (`iter::once(0).chain(…)`); subsequent entries = one past each line terminator, with `\r` inside `\r\n` filtered out.

### Decisive source
```rust
// location.rs:161-171 — match BOTH \n and \r but drop the \r half of \r\n
// so CRLF yields ONE line start, not two
Self(
    std::iter::once(0)
        .chain(source.match_indices(&['\n', '\r']).filter_map(|(i, _)| {
            let bytes = source.as_bytes();
            match bytes[i] {
                // Filter out the `\r` in `\r\n` to avoid counting the line break twice
                b'\r' if i + 1 < bytes.len() && bytes[i + 1] == b'\n' => None,
                _ => Some(i + 1),
            }
        }))
        .map(|i| TextSize::try_from(i).expect("integer overflow"))
        .collect(),
)
```

**Flow:** scan for either terminator byte → lone `\r` (classic Mac) and `\n` (Unix) both start a new line → `\r\n` (Windows) counts once → table feeds binary-search location lookup for span starts in code frames/headers.
**Invariant:** The filter's lookahead guard (`i + 1 < bytes.len()`) also handles a trailing `\r` at EOF as a real line break. A porter matching only `\n` mis-reports every column on CRLF files by drifting lines; matching both without the filter splits CRLF into two phantom lines.
**Probe:** Three in-file unit tests pin all three ending styles: `location.rs:386-399` (`line_starts_with_carriage_return_line_feed`: "a\r\nb\r\nc" → [0,3,6]), :401-414 (`…_carriage_return`: "a\rb\rc" → [0,2,4]), :416-429 (`…_line_feed`: [0,2,4]).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "LineIndexBuf", limit: 10, fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt the three-way terminator handling verbatim. Adapt the offset type. Omit the transmute view if your host can afford a plain Vec wrapper.
