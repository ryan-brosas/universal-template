<!-- capsule-v2 -->
# TextEdit dictionary diff — how do you serialize an editor patch as interned ops and replay it against the OLD string?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** a fix needs to cross a process/protocol boundary as data, compress huge unchanged middles, and still reconstruct the new text — what representation makes replay exact?

## The TextEdit seam
**Path/Symbol:** `crates/biome_text_edit/src/lib.rs` — `TextEdit { dictionary: String, ops: Vec<CompressedOp> }` (:24-27), `TextEditBuilder::intern` (:175-212), `equal` (:214-238), `new_string` (:117-147), `compress_equal_op` (:297-317), `with_unicode_words_diff` (:266-287).
**Signature:** `pub fn new_string(&self, old_string: &str) -> String`; `fn intern(&mut self, value: &str) -> TextRange`.
**Data Shape:** ops are `DiffOp{Equal|Insert|Delete{range}}` (ranges into the DICTIONARY, not the document) plus the compression marker `EqualLines { line_count: NonZeroU32 }`. Equal ranges index UNCHANGED text; Insert/Delete index changed text; nothing stores the old document.

### Decisive source
```rust
// lib.rs:131-142 — EqualLines replay is line-based over the OLD string and the
// count is +1 (split_inclusive keeps the \n; take(line_count + 1)):
CompressedOp::EqualLines { line_count } => {
    let start = u32::from(input_position) as usize;
    let input = &old_string[start..];
    let line_break_count = line_count.get() as usize + 1;
    for line in input.split_inclusive('\n').take(line_break_count) {
        output.push_str(line);
        input_position += TextSize::of(line);
    }
}
```
```rust
// lib.rs:179-195 — intern's binary search treats a LONGER stored entry containing
// the value as EQUAL (prefix reuse), returning the shared prefix range:
match entry.len().cmp(&value_bytes.len()) {
    // If all bytes in the shared sub-slice match, the dictionary entry is allowed
    // to be longer than the text being inserted
    Ordering::Greater => Ordering::Equal,
    ordering => ordering,
}
...
Ok(index) => {
    let range = self.index[index];
    let len = value_len.min(range.len());
    TextRange::at(range.start(), len)
}
```
**Flow:** builder ops come from `with_unicode_words_diff` (similar crate, newline-terminated unicode-word granularity) or manual equal/insert/delete; every `equal()` longer than 2+2 context lines around ≥1 skipped middle line compresses into Equal(start)+EqualLines(n)+Equal(end) (`compress_equal_op`, context const = 2 :295). Replay walks ops tracking `input_position` into old_string: Equal copies from dictionary and advances; Insert copies without advancing; Delete advances without copying. Dictionary dedup means two identical inserts share one range — mutating the dictionary after finish would alias both.
**Invariant:** ranges are dictionary-relative, never document-relative; compressed Equal segments only appear where the surrounding lines were kept verbatim so replay from old_string is byte-exact; interning may return a PREFIX of a longer entry (len = min), which is why get_text slices by that returned length.
**Probe:** in-crate tests pin all three contracts: `compress_short` returns None for ≤4-line equals (:326-337), `compress_long` returns exactly `("\nstart 1\nstart 2", NonZeroU32(3), "end 1\nend 2\n")` (:340-361), `new_string_compressed` round-trips a 7-line file through compression to the exact NEW text (:364-385).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "TextEditBuilder intern compress_equal_op new_string", limit: 10, fields: ["signature", "name", "file"] });
// intern lib.rs 175-212; compress_equal_op 297-317 (line-exact)
```

## Verdict
Adopt dictionary-interleaved op lists with line-count compression and old-string replay; adapt tokenization granularity per consumer; omit serde/schema derives unless crossing protocols. Coverage caveat: strongly unit-pinned in-crate including the off-by-one replay contract.
