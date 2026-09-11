<!-- capsule-v2 -->
# date GNU-format plane — modifier grammar, military timezones with day rollover, comment stripping

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85` (uutils port); Codebase Memory `oh-my-pi`. **Question:** Which GNU date extensions beyond strftime must a port reproduce?

## format_modifiers + parse helpers
**Path/Symbol:** `crates/pi-builtins/src/date.rs:` modifier doc (:9-38), `FORMAT_SPEC_REGEX` (:81-82), `format_with_modifiers_if_present` (:90-110), `DayDelta` (:904-912), `escape_invalid_bytes` (:932-946), `strip_parenthesized_comments` (:959-983), `parse_military_timezone_with_offset` (:998+), `-v` adjustments (:1148+), relative-parse test :2292.
**Signature:** `fn format_with_modifiers_if_present(date: &Zoned, fmt: &str, config) -> Option<Result<String, FormatError>>`; `fn parse_military_timezone_with_offset(s: &str) -> Option<(i32, DayDelta)>`.
**Data Shape:** Modifier regex `%([_0^#+-]*)(\d*)(:*[a-zA-Z])`: flags `- _ 0 ^ # +`, optional width; quick `any()` pre-scan avoids the formatting path entirely when no modifiers present. Military zones: A–I=+1..+9 (J skipped), K–M=+10..+12, N–Y=−1..−12, Z=0; optional 1–2 digit hour offset added.

### Decisive source
```rust
/// Strip parenthesized comments ... If parentheses are unbalanced, everything
/// from the unmatched '(' onwards is ignored.
/// "2026(comment)-01-05" -> "2026-01-05"   |  "1(ignore to eol" -> "1"
/// "(" -> ""                              |  "((foo)2026-01-05)" -> ""
```
```rust
// Examples: "m" -> 12 (noon UTC), "m9" -> 21 (9pm UTC), "a5" -> 4 (4am UTC NEXT DAY)
// DayDelta::Next / ::Previous capture midnight crossings when the offset applies.
DayDelta::Next => format_date_with_epoch_fallback(now.tomorrow()),
```

**Flow:** parse date string → strip balanced/unbalanced parenthesized comments → tokenize words → military-zone tokens may roll the DATE backward/forward → `-v` unit adjustments compose (+1d, −2m; epoch fallback when result underflows) → format: fast path plain strftime, modifier path re-renders each spec with padding/case flags; invalid UTF-8 in output escaped as `\NNN` octal.
**Invariant:** (1) The None-return of the modifier scan is a performance contract — standard formats never pay regex cost. (2) Width overflow is a typed error (`FieldWidthTooLarge`) naming specifier + width. (3) Comment stripping is depth-counted, not regex, and truncates at depth-1 unmatched `(`. (4) Relative parsing ("yesterday 10:00 GMT") anchors against an injectable NOW for tests.
**Probe:** deterministic anchors: `grep -c 'fn parse_military_timezone_with_offset' crates/pi-builtins/src/date.rs` = 1; direct tests: date.rs:2292 `parses_relative_abbreviation_against_pinned_now` plus comment-stripping/octal-escape pins in the same module.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "date military timezone day delta modifiers", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps (date.rs:998).

## Verdict
Adopt the modifier pre-scan + depth-counted comment stripping + DayDelta rollover modeling for any strftime+GNU superset formatter. Adapt jiff types to your time library; keep the J-skipping military table and unbalanced-paren truncation rule.
