<!-- capsule-v2 -->
# tr set grammar — ambiguous octal warning, ranges, repeat/star, equivalence classes

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85` (uutils port); Codebase Memory `oh-my-pi`. **Question:** Where does tr's escape grammar deviate from naive octal parsing, and what warnings must a faithful port emit?

## octal-with-warning parser
**Path/Symbol:** `crates/pi-builtins/src/tr.rs:` `parse_octal_with_warning` (:454-472), `parse_octal_up_to_three_digits` (:474-480), `parse_octal_two_digits` (:483-488), `parse_char_range` backwards-range error (:527-543), `parse_char_star` (:545-549), unescaped-backslash-at-end warning (:924), tests :1058/:1170.
**Signature:** `fn parse_octal_with_warning(input: &[u8]) -> IResult<&[u8], (u8, Option<String>)>`.
**Data Shape:** Unambiguous contexts use up-to-three-digit octal; the SET2 boundary context uses EXACTLY-two digits with a GNU-mirroring warning when three were written: `\400` → byte `\40` + literal `0`.

### Decisive source
```rust
let (rest, value) = Self::parse_octal_two_digits(digits)?;
let warning = if let Ok(origin_octal) = std::str::from_utf8(digits) {
	let actual_octal_tail = std::str::from_utf8(&digits[..2]).unwrap();
	let outstand_char = char::from_u32(digits[2] as u32).unwrap();
	format!(
		"the ambiguous octal escape \\{origin_octal} is being interpreted as the 2-byte \
		 sequence \\0{actual_octal_tail}, {outstand_char}"
	)
} else { "invalid utf8 sequence".to_string() };
```

**Flow:** sets parse left-to-right: escapes (`\n` table, octal, `\\`) → `a-z` ranges (backwards = BadSequence error) → `[c*n]` repeat semantics (star fills to set1 length; n=0 allowed) → ` [=c=] ` equivalence classes → translate/squeeze/delete pipelines over bytes.
**Invariant:** (1) The two-vs-three digit split is CONTEXT-dependent — same escape spelling parses differently in set1 vs set2 positions; ports that normalize octal globally break GNU scripts relying on `\400` → `\` + `0`. (2) Warnings go to stderr and processing CONTINUES. (3) A trailing lone backslash warns "not portable" instead of erroring.
**Probe:** direct tests pin both: `tr.rs:1170 reports_ambiguous_octal_escape_warning` (asserts the exact warning text incl. `\400` → 2-byte sequence), :1058 `expands_literals_ranges_and_escapes`; deterministic anchor `grep -c 'ambiguous octal escape' crates/pi-builtins/src/tr.rs` ≥ 2.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "tr octal escape warning ambiguous", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps (tr.rs:454).

## Verdict
Adopt the context-sensitive octal grammar + warning-and-continue policy for any tr-family translator. Adapt nom combinators to your parser lib; pin the warning text byte-exact — scripts grep for it.
