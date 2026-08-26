<!-- capsule-v2 -->
# Preferred-quote election kernel — how do you pick the quote style that minimizes escapes, identically across language formatters?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** given a configured quote style and a token's contents, when should the formatter override to the other quote — and where does that decision live so JS/CSS stay consistent?

## Count-and-swap with per-language guards
**Path/Symbol:** JS `crates/biome_js_formatter/src/utils/string_utils.rs` — `FormatLiteralStringToken::compute_string_information` (:144-194), `LiteralStringNormaliser::normalise_text` parent-kind dispatch (:239-249), `normalise_directive` preserve-contract (:268-283), `normalise_type_member` TS guard (:313-327), `normalise_string_literal` owned-forces-requote (:330-349), `swap_quotes` (:356-371). CSS twin `crates/biome_css_formatter/src/utils/string_utils.rs` — `compute_string_information` non-literal shortcut (:178-199), `preferred_quote_style_for_contents` iterator kernel (:121-148).
**Signature:** `fn compute_string_information(&self, chosen_quote: QuoteStyle) -> StringInformation`; `pub(crate) fn preferred_quote_style_for_contents(contents: impl Iterator<Item = impl AsRef<str>>, chosen_quote: QuoteStyle) -> QuoteStyle`.
**Data Shape:** `StringInformation { current_quote, preferred_quote, raw_content_has_quotes? }` (JS carries the extra has-quotes flag; CSS makes `current_quote: Option<QuoteStyle>` because CSS tokens like url-raw or plain identifiers arrive UNQUOTED). Parent kinds: Expression / Directive / ImportAttribute / Member.

### Decisive source
```rust
// js string_utils.rs:187-193 — swap IFF strictly more chosen-style quotes inside:
preferred_quote: if chosen_quote_count > alternate_quote_count {
    alternate_quote
} else {
    chosen_quote
},
raw_content_has_quotes: chosen_quote_count > 0 || alternate_quote_count > 0,

// :269-276 — directives NEVER get normalized (prettier#1555): escapes are semantic:
if string_information.raw_content_has_quotes {
    Cow::Borrowed(self.get_token().text_trimmed())
} else {
    self.swap_quotes(self.raw_content(), string_information)
}

// :337-347 — content was rebuilt ⇒ MUST take the new quotes (borrowed path may keep old):
match polished_raw_content {
    Cow::Borrowed(raw_content) => self.swap_quotes(raw_content, &string_information),
    Cow::Owned(mut s) => {
        s.insert(0, preferred_quote.as_char());
        s.push(preferred_quote.as_char());
        ...
    }
}
```
**Flow:** count unescaped-ish occurrences of both quote bytes in the quoteless content; strict-greater flips the preference. Dispatch on parent kind FIRST: directives bypass normalization entirely (their escapes are behavior — `"use\x20strict"` is NOT `"use strict"`), import attributes and type members additionally require the content to be a bare identifier or exact-roundtrip number (`can_remove_number_quotes_by_file_type` refuses TypeScript ALWAYS for numeric members and refuses floats whose `parse::<f64>()` doesn't round-trip), expressions run the full pipeline.
**Invariant:** directive immutability — a directive containing ANY quote byte is returned `Cow::Borrowed(text_trimmed())`, never re-quoted, never unescaped. The TS numeric-member refusal exists because `'123'` as a computed/class member means something different than the number `123`. The owned-content ⇒ forced-requote rule closes the gap where normalization already allocated: leaving stale outer quotes around rewritten content would produce mismatched delimiters.
**Probe:** `crates/biome_js_formatter/src/utils/string_utils.rs` test mod :374-555 pins borrowed-preservation across Directive/String/Member tokens via `assert_borrowed_token` + tree-built tokens (`generate_syntax_token`). Greps: `grep -nF 'chosen_quote_count > alternate_quote_count' crates/biome_js_formatter/src/utils/string_utils.rs` → 1 hit :187; `grep -nF 'prettier/prettier/issues/1555' …` → 1 hit :270; `grep -nF 'parsed.to_string() == text_to_check' …` → 1 hit :305; `grep -nF 'CSS_STRING_LITERAL' crates/biome_css_formatter/src/utils/string_utils.rs` → :6 use + :184 shortcut.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"compute_string_information"}'
# resolves BOTH twins line-exact: js FormatLiteralStringToken Method 144-194,
# css FormatLiteralStringToken Method 178-199 (non-literal shortcut differs)
```

## Verdict
Adopt the strict-greater election + parent-kind dispatch + directive freeze verbatim; adapt the member/attribute legality ladders to your language's semantics; omit the CSS `Option<QuoteStyle>` shape only if your grammar guarantees quoted tokens. Coverage: both files indexed clean (`no_recorded_issue` @ 2026-08-16T00:20:04Z).
