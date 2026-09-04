<!-- capsule-v2 -->
# Suppression comment parser — how do you parse `biome-ignore` comments across every comment syntax without a regex?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** suppression comments must be recognized inside `//`, `/* */`, `#`, and HTML comments, case-insensitively, multi-line, with several categories per line — what is the exact grammar and its sharp edges?

## The biome_suppression seam
**Path/Symbol:** `crates/biome_suppression/src/lib.rs` — `parse_suppression_comment` (:87-192), `parse_suppression_line` (:328-413), `parse_category` (:425-442), `offset_from` (:450-467), `SuppressionKind` (:57-66).
**Signature:** `pub fn parse_suppression_comment(base: &str) -> impl Iterator<Item = Result<Suppression<'_>, SuppressionDiagnostic>>`; grammar `// biome-ignore { <category> { (<value>) }? }+: <reason>`.
**Data Shape:** `Suppression { categories: Vec<(&'static Category, Option<&str> subcategory, Option<&str> value)>, reason: &'a str, kind: SuppressionKind, range, reason_range }` — ranges are RELATIVE to the start of the comment token (`3..=15` for the ignore keyword in `// biome-ignore lint: foo`, :41-53).

### Decisive source
```rust
// lib.rs:127-151 — hand-rolled case/underscore-insensitive matcher; NOTE the
// second char of "bi-": ['-', '_'] accepts biome_ignore too:
const PATTERN: [[char; 2]; 12] = [
    ['b','B'], ['i','I'], ['o','O'], ['m','M'], ['e','E'],
    ['-','_'], ['i','I'], ['g','G'], ['n','N'], ['o','O'], ['r','R'], ['e','E'],
];
// Checks for `/biome[-_]ignore/i` without a regex, or skip the line entirely
for pattern in PATTERN {
    line = line.strip_prefix(pattern)?;   // non-matching lines are SILENTLY skipped (None)
}
```
```rust
// lib.rs:176-180 — the keyword range is found by re-searching the WHOLE comment,
// so a line mentioning the keyword later shadows the real one:
let range = base.find(kind.as_str()).map(|start| { ... })?;
```
**Flow:** strip comment opener (`#` → 1 char, `<!--` → 4, else 2); block comments strip `*/` suffix tolerantly (also bare `*` or `/` — unclosed block comments still parse, tested :643-676) then per-line trim leading whitespace AND `*`. Match `-all` / `-start` / `-end` suffixes (both cases) to pick `SuppressionKind`. Then `parse_suppression_line` loops categories until a colon: separator ∈ {`:`,`(`,whitespace}; `(` demands a closing paren and pushes `(category, subcategory, Some(value))`; unknown category strings error with `suppressions/parse`; missing reason errors. `lint/plugin/<name>` is special-cased BEFORE static category parse because plugin names are dynamic (:432-436). Diagnostics carry spans rebased onto the whole comment via `offset_from` (raw pointer arithmetic — substr MUST be within base).
**Invariant:** lines that merely mention other text are silently ignored (return None) — only well-formed `biome[-_]ignore` lines produce results; the reason is MANDATORY; ranges are comment-relative so callers must add the piece offset (analyzer's `to_analyzer_suppressions` does `piece_range.add_start(...)` for every range, lib.rs of biome_analyze :726-737). A porter who forgets the `-all/-start/-end` suffix ladder turns file-wide suppressions into line suppressions.
**Probe:** `crates/biome_suppression/src/lib.rs` tests_suppression_kinds :476-546 pin exact `range`/`reason_range` TextSizes for classic/all/start/end (`TextRange::new(3,15)` etc.); `check_parse_category` :780-805 pins `(None,None)` empty, plugin split, and invalid-category Err; `check_offset_from` :808-818 pins pointer-offset behavior incl. full-length substring.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_suppression_line parse_category SuppressionKind", limit: 10, fields: ["signature", "name", "file"] });
// parse_suppression_line lib.rs 328-413; parse_category 425-442; check_parse_category test 780-805 (line-exact)
```

## Verdict
Adopt the regex-free prefix-ladder parser, tolerant block-comment handling, mandatory-reason rule, and comment-relative ranges with caller-side rebasing; adapt the category vocabulary per host; omit the `lint/plugin` dynamic-subcategory special case unless porting plugins. Coverage caveat: unit-tested directly in-crate with exact byte offsets — strong pins.
