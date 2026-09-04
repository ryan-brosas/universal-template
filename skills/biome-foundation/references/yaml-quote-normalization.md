<!-- capsule-v2 -->
# YAML quote normalization — the pinning ladder that decides when a scalar's quotes may change

**Source:** biome MIT `main@6f7774dc` (drift plane pass 13); Codebase Memory `biome`. **Question:** How does the YAML formatter re-quote scalars toward the configured style WITHOUT ever changing meaning? (The escape/quote interaction is where naive ports corrupt data.)

## normalize_quotes (biome_yaml_formatter/src/flow_scalar.rs)
**Path/Symbol:** `crates/biome_yaml_formatter/src/flow_scalar.rs:122-174` (`normalize_quotes`), `:131-147` (pin detection), `:152-166` (opposite-style fallbacks).
**Signature:** `normalize_quotes(value: &str, quote_style: QuoteStyle) -> Cow<'_, str>` — returns Borrowed when unchanged.

### Decisive source
```rust
// flow_scalar.rs:131-147 — the pin rules
let pinned = match quote {
    QuoteStyle::Single => raw.contains('\\'),        // backslash is CONTENT in single quotes;
                                                     // double-quoting would read it as an escape
    QuoteStyle::Double => { /* scan: any backslash NOT followed by '"' pins */ }
};
```
```rust
// :116-121 doc — the whole decision table in four lines
/// A quote character in the text picks the opposite quotes regardless of the
/// preferred style, so it doesn't have to be escaped. Escape sequences only
/// exist in double quoted scalars and only `\"` has a single quoted
/// equivalent, so text with any other escape keeps its double quotes; a
/// backslash in a single quoted scalar is content that double quotes would
/// misread as an escape, so such text keeps its single quotes
```

**Flow:** detect enclosing quote pair (`bytes.first()`/`last()`; len≥2) → unquoted plain = untouched → pinned? keep → contains `"`? to-single via `'…'` with `''` doubling (from double: strip `\"` escapes first) → contains `'`? to-double with `''`→`'` unfolding → else apply preferred style.
**Invariant:** BOTH quote kinds in one text resolve to SINGLE with doubling (`"it's \"quoted\""` → `'it''s "quoted"'`, test :216). Empty string `''` still normalizes (`to_double("''") == "\"\""`, test :203). The trailing-whitespace trim happens BEFORE normalization at the call site (:38 `text_trimmed().trim_end()`) — closing quotes sit against trimmed content but the LAST line's internal trailing ws is content (see flow-scalar capsule sibling).
**Probe:** `grep -c '#\[test\]' crates/biome_yaml_formatter/src/flow_scalar.rs` → `5`; `grep -n 'fn normalize_quotes' crates/biome_yaml_formatter/src/flow_scalar.rs` → `122:`; `grep -nF 'raw.replace' crates/biome_yaml_formatter/src/flow_scalar.rs` → `157:` (escape-strip before single-quoting); `grep -n 'Cow::Borrowed(value)' crates/biome_yaml_formatter/src/flow_scalar.rs | wc -l` → `5`.

## Multiline context (same file, FormatFlowScalar)
Line structure preserved; blank lines emitted as literal `\n` TEXT because the printer collapses consecutive line-break elements and appends indentation after each (:68-90 comments) — literal text is the only way to keep exact blank-line count inside a folded value.
**Probe:** `grep -cF 'text("\n", None)' crates/biome_yaml_formatter/src/flow_scalar.rs` → `2` (blank-line write + prev_empty terminator).

---
**Verdict:** ADOPT the ladder verbatim; every branch is backed by a unit test that doubles as the spec.
