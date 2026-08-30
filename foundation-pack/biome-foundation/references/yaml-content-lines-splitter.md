<!-- capsule-v2 -->
# ContentLines — the lone-`\r` splitter that str::lines cannot replace

**Source:** biome MIT `main@6f7774dc` (drift plane pass 13); Codebase Memory `biome`. **Question:** Why does YAML scalar handling need a custom line iterator, and what's the exact break-byte grammar?

## The iterator (biome_yaml_formatter/src/content_lines.rs, 52L)
**Path/Symbol:** `crates/biome_yaml_formatter/src/content_lines.rs:1-9` (doc = spec), `:32-52` (`Iterator` impl).
**Signature:** `ContentLines::new(text) -> Self`; `ends_with_break()`, `has_remaining()`; yields `&str` lines.

### Decisive source
```rust
// content_lines.rs:4-6 — the reason str::lines is WRONG here
/// [str::lines] can't be used here because it doesn't split at a lone `\r`,
/// which YAML accepts as a line break. Leaving one embedded in a line would
/// print a `\r` the printer's line ending option never normalized.
```
```rust
// :39-46 — CRLF enters at '\r' and consumes BOTH bytes
match text.find(['\n', '\r']) {
    Some(index) => {
        let bytes = text.as_bytes();
        let break_len = match bytes[index] {
            b'\r' if bytes.get(index + 1) == Some(&b'\n') => 2,
            _ => 1,
        };
        self.rest = Some(&text[index + break_len..]);
        Some(&text[..index])
    }
    None => Some(text),
}
```

**Flow:** find first of `\n|\r` → lone `\n` or `\r` consumes 1 byte; `\r\n` consumes 2 → trailing-break text yields a FINAL EMPTY LINE (that's how "ends with break" is represented; `ends_with_break()` lets callers distinguish).
**Invariant:** The final-empty-line convention is load-bearing for callers deciding whether to trim (FormatFlowScalar keeps last line's trailing ws via `has_remaining()`); a porter swapping in `str::lines()` silently corrupts old-Mac/CR-LF-mixed YAML AND breaks last-line trimming. Comment notes `\r\n` can never be entered mid-pair because the search matches whichever byte comes first.
**Probe:** `grep -cF "b'\r'" crates/biome_yaml_formatter/src/content_lines.rs` → `1` (the CRLF-pair arm :43); `grep -n 'ends_with_break' crates/biome_yaml_formatter/src/content_lines.rs` → `22:`; `grep -rl 'ContentLines::new' crates/biome_yaml_formatter/src/ | sort` lists exactly THREE consumers — `flow_scalar.rs`, `utils.rs`, and `yaml/auxiliary/block_content.rs` (the block-scalar kernel; the def file itself never calls `new`).

---
**Verdict:** ADOPT as-is wherever YAML text is reflowed; 52 lines, no dependencies, test coverage lives in its consumers.
