<!-- capsule-v2 -->
# String-literal content normalizer — how do you escape the preferred quote, unescape the losing one, and normalize CRLF in ONE byte pass?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** when a formatter changes a string literal's quote style, which escapes must be added, which removed, and how do newlines survive — all without allocating unless something actually changed?

## The single-pass escape rewriter
**Path/Symbol:** `crates/biome_formatter/src/token/string.rs` — `normalize_string` (:47-102), `Quote { Double, Single }` with `as_char/as_byte/other` (:3-28).
**Signature:** `pub fn normalize_string(raw_content: &str, preferred_quote: Quote, quotes_will_change: bool) -> Cow<'_, str>`.
**Data Shape:** input = quoteless string-literal CONTENT (callers strip the outer quotes). Output = `Cow::Borrowed` iff no change was made (`copy_start == 0 && reduced_string.is_empty()`, :95); otherwise an Owned rebuilt string. Three transformations fused into one loop: escape unescaped preferred quotes, unescape alternate quotes (only when quotes will change), and rewrite `\r\n` → `\n`.

### Decisive source
```rust
// string.rs:60-74 — backslash lookahead drives BOTH unescape decisions:
b'\\' => {
    if let Some((escaped_index, escaped)) = bytes.next() {
        if escaped == b'\r' {
            // If we encounter the sequence "\r\n", then skip '\r'
            if let Some((next_byte_index, b'\n')) = bytes.next() {
                reduced_string.push_str(&raw_content[copy_start..escaped_index]);
                copy_start = next_byte_index;
            }
        } else if quotes_will_change && escaped == alternate_quote {
            // Unescape alternate quotes if quotes are changing
            reduced_string.push_str(&raw_content[copy_start..byte_index]);
            copy_start = escaped_index;
        }
    }
}
```
**Flow:** iterate raw bytes; on `\` peek one char — `\r` begins a CRLF pair whose `\r` is dropped, alternate-quote becomes unescaped ONLY under `quotes_will_change`, everything else copies verbatim. On bare `\r` drop it when followed by `\n`. On an UNESCAPED preferred-quote byte splice in a backslash (:87-91) because enclosing strings may switch quotes later. Copy-tail + return.
**Invariant:** the alternate-quote unescape is GATED on `quotes_will_change` — unconditionally unescaping would corrupt strings that keep their original quote style (test `normalize_quotes`: `normalize_string(r"\'", Quote::Double, false)` must stay `\'`). Escaped-CRLF handling means `a\` + newline + `b` keeps its line continuation while still normalizing the terminator (test `normalize_newline` third case). The borrowed-vs-owned split is observable contract, not an optimization detail.
**Probe:** `crates/biome_formatter/src/token/string.rs` unit tests :104-150 pin all three transformations (`normalize_newline`, `normalize_escapes`, `normalize_quotes` incl. the false-flag cases). Greps: `grep -nF 'quotes_will_change && escaped == alternate_quote' …token/string.rs` → 1 hit :68; `grep -c 'If we encounter the sequence' …` → 2 (both CRLF sites).
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"normalize_string"}'
# biome.crates.biome_formatter.src.token.string normalize_string Function 47-102
```

## Verdict
Adopt the fused pass + Cow discipline verbatim for any quote-policy change; adapt the escape vocabulary to your language's string grammar; omit the preferred-quote pre-escaping only if your port never switches enclosing quotes after this point. Coverage: file indexed clean (`no_recorded_issue`/`metadata_match` @ 2026-08-16T00:20:04Z).
