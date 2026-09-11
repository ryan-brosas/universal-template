<!-- capsule-v2 -->
# Validated option value objects — how do you keep formatter options impossible to hold invalid while parsing them from three different sources?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** line/indent widths arrive from JSON config, CLI strings, and programmatic APIs — what is the pattern that guarantees a stored option value is always in range without scattering checks?

## Newtype + triple-constructor validation
**Path/Symbol:** `crates/biome_formatter/src/lib.rs` — `IndentWidth(u8)` (:302-317, MIN 0 / MAX 24, default 2), `LineWidth(u16)` (:403-418, MIN 1 / MAX 320, default 80), `ParseFormatNumberError` (:474-497), `IndentWidthFromIntError` (:543), `LineWidthFromIntError` (:561); enum options `QuoteStyle` (:590, Double default, `from_byte`/`as_char`/`as_html_entity`/`other()` swap), `LineEnding` (:151, Lf/Crlf/Cr/Auto with `as_str()` cfg(windows) for Auto), `IndentStyle` (:99, Tab default, `DEFAULT_SPACES = 2`), `Expand` (:909, Auto/Always/Never), `BracketSpacing(bool)` (:675, default true), `DelimiterSpacing(bool)` (:735), `BracketSameLine(bool)` (:821), `TrailingNewline(bool)` (:862, default true), `AttributePosition` (:784).
**Signature:** `impl TryFrom<u16> for LineWidth { type Error = LineWidthFromIntError }`; `fn deserialize(ctx, value, name) -> Option<Self>` via `TextNumber::deserialize`.
**Data Shape:** each width is a private-field newtype; the ONLY constructors are `TryFrom<uN>` (range-checked), `FromStr` (parse then try_from), and the two deserializer impls (manual `Deserializable` reporting out-of-bound diagnostics, serde shim mapping errors to `serde::de::Error::custom`). No public tuple constructor ⇒ an inhabited `LineWidth` cannot exceed 320.

### Decisive source
```rust
// lib.rs:326-339 — manual Deserializable: parse text, report range diagnostic on failure:
let value_text = TextNumber::deserialize(ctx, value, name)?;
if let Ok(value) = value_text.parse::<Self>() {
    return Some(value);
}
ctx.report(DeserializationDiagnostic::new_out_of_bound_integer(
    Self::MIN, Self::MAX, value.range(),
));
None
```
```rust
// lib.rs:545-554 — the copy-paste BUG a porter must NOT reproduce:
impl std::fmt::Display for IndentWidthFromIntError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        writeln!(f,
            "The indent width should be between {} and {}, got {}",
            LineWidth::MIN,   // <-- prints 1..=320 bounds for an INDENT error
            LineWidth::MAX,
            self.0,
        )
    }
}
```
**Flow:** JSON path → `TextNumber::deserialize` → `FromStr` → `TryFrom` → either `Some(valid)` or one reported diagnostic + `None` (caller keeps the type's `Default`). CLI-string path → `FromStr`. Integer path → `TryFrom`. All converge on the same range check; `Merge` derive lets config layering combine values only when both are valid instances.
**Invariant:** validation happens at construction, never at use — printer code reads `.value()` unguarded. The out-of-range JSON test pins the recovery semantics too: `test_out_of_range_line_width` (:2916) asserts BOTH the message `"The number should be an integer between 1 and 320."` AND that the field falls back to `LineWidth(80)` (:2950). Note `IndentStyle`/`LineEnding`/`QuoteStyle` FromStr impls are case-sensitive exact-literal matches with TODO-replace-me static-string errors.
**Probe:** `grep -c 'new_out_of_bound_integer' crates/biome_formatter/src/lib.rs` → 2; `grep -c 'TextNumber::deserialize' …` → 2; `sed -n '545,554p' …` shows the wrong-bounds Display; direct test `test_out_of_range_line_width` :2916 (message + default-fallback assertions); `test_strip_trailing_newlines` :2956 covers the adjacent `Printed` API.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"LineWidthFromIntError"}'
# biome.crates.biome_formatter.src.lib LineWidthFromIntError Struct 561-561
```

## Verdict
Adopt the newtype-with-private-field + TryFrom-only construction pattern for any user-supplied numeric option; adapt the diagnostic messages (and FIX the cross-wired MIN/MAX Display bug if porting verbatim — cite it as upstream behavior, not intent); omit the serde/schema cfg shims if your host has no config-schema generation. Coverage: no_recorded_issue on all sibling files; lib.rs partial only inside tests.
