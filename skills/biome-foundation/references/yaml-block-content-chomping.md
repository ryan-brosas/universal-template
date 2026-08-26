<!-- capsule-v2 -->
# YamlBlockContent chomping kernel — how block-scalar content lines are selected, re-indented, and who owns the trailing breaks?

**Source:** biome MIT `main@6f7774dc` (YAML stack, pass 14 audit-discovered seam); Codebase Memory `biome`. **Question:** A porter formatting YAML block scalars (`|`, `>`, with `-`/`+` chomping and indentation indicators) must reproduce exactly which token lines count as content, how base indentation is derived, where less-indented trailing comment lines go, and which side owns every trailing blank line under Keep chomping.

## The single-pass stats + chomping matrix (yaml/auxiliary/block_content.rs)
**Path/Symbol:** `crates/biome_yaml_formatter/src/yaml/auxiliary/block_content.rs:22-229` (`FormatYamlBlockContent::fmt_fields`), `:301-326` (`parent_headers`), `:338-394` (`ContentStats::new`), `:396-412` (`closes_last_document`), `:277-297` (`FormatContentLine`).
**Signature:** `parent_headers(node) -> (Chomping, Option<usize>)`; `ContentStats::new(lines, explicit_indent) -> Self { line_count, trimmed_count, first_indent, scalar_end }`; `kept_lines = match (chomping, scalar_end)`.

### Decisive source
```rust
// block_content.rs:52-63 — the whole chomping decision table
let kept_lines = match (chomping, scalar_end) {
    // With a trailing comment region the token continues past the
    // content, whose trailing blank lines all belong to it
    (Chomping::Keep, Some(scalar_end)) => scalar_end,
    // The line break terminating the last line is printed by the
    // enclosing structure, so the line it opens isn't content
    (Chomping::Keep, None) => stats.line_count.saturating_sub(usize::from(ends_with_break)),
    // Trailing blank lines are dropped
    (Chomping::Clip | Chomping::Strip, _) => stats.trimmed_count,
};
```
```rust
// :381-389 — scalar_end + the whitespace-beyond-base-is-CONTENT rule
if spaces < base_indent {
    stats.scalar_end = Some(stats.line_count.saturating_sub(1));
} else {
    stats.trimmed_count = stats.line_count;
}
...
} else if base_indent.is_some_and(|base_indent| spaces > base_indent) {
    // A line holding only whitespace up to the base indentation
    // is an empty line; more whitespace than that is content
    stats.trimmed_count = stats.line_count;
}
```

**Flow:** read headers from parent (`|+`/`>-`/explicit digit indicator; duplicates resolved last-wins per header kind) → `ContentLines::new(token_text).skip(1)` (FIRST line is the header line's tail, never content) → one pass computes stats: base_indent = explicit indicator else first non-blank line's spaces; a line indented LESS than base ends the scalar (the LEXER includes such trailing-comment lines inside the token — everything from there on is the trailing region); whitespace-only lines beyond base are content, not empty → select `kept_lines` per matrix → print each line through `FormatContentLine` (strip `min(leading_spaces, base_indent)`, re-indent by formatter nesting or absolute `align(explicit_indent−1+ancestors)`) → trailing region printed at **column zero** via `base_indent: usize::MAX` (:197) + `dedent_to_root` (:211/:223).
**Invariant:** Base indent is REPLACED, never normalized: original deeper indentation is content and survives verbatim. An explicit indicator makes indentation ABSOLUTE (`indicator−1` plus enclosing block-collection depth). Blank lines BEFORE the first non-blank line can neither set nor end anything — the first non-blank line after them always wins both races.

## Keep-chomping break ownership (the porting trap)
**Invariant chain:** With `|+`, trailing blank lines BELONG TO THE SCALAR, but the parser leaves them in the NEXT token's leading trivia — recovered by walking those trivia pieces (:83-117): the FIRST newline terminates the last content line (opens nothing); whitespace pending before a newline becomes that blank line's text; a comment piece STOPS recovery ("a comment and anything after it isn't part of the scalar"). If the scalar closes the LAST document (`closes_last_document`: walk up, every node is a last child until root), it must print its OWN final break (:136-143) — unless comments follow (:131-135, the comment prints the blank line above itself instead). The EMPTY `|+` at EOF still owns all breaks after its header, counted from next-token trivia (:156-171). Missing any leg duplicates or drops trailing blank lines — pinned by fixtures `tests/specs/yaml/block_scalar/{keep_trailing_blank_lines,empty_keep_at_eof}.yaml`.
**Probe:** `grep -c 'Chomping::Keep' crates/biome_yaml_formatter/src/yaml/auxiliary/block_content.rs` → `6`; `grep -n 'base_indent: usize::MAX' crates/biome_yaml_formatter/src/yaml/auxiliary/block_content.rs` → `197:`; `grep -n 'fn closes_last_document' crates/biome_yaml_formatter/src/yaml/auxiliary/block_content.rs` → `401:`; `grep -n 'struct ContentStats' crates/biome_yaml_formatter/src/yaml/auxiliary/block_content.rs` → `338:`; `grep -c '#\[test\]' crates/biome_yaml_formatter/src/yaml/auxiliary/block_content.rs` → `0` (NO unit tests here — behavior spec lives in the fixture snapshots; `less_indented_comment_lines.yaml.snap` pins the column-0 trailing-comment reprint, `keep_trailing_blank_lines.yaml.snap` pins break preservation).

## Shared line state across one scalar (:254-297)
**Data Shape:** `Cell<LineState> { any_line, prev_empty }` threaded through every `FormatContentLine` of the scalar. Blank lines emit literal `text("\n", None)` (4 sites) so the printer can neither collapse consecutive breaks onto them nor leave indentation; a following non-blank line first emits the closing `\n` then `hard_line_break()` + text.
**Probe:** `grep -cF 'text("\n", None)' crates/biome_yaml_formatter/src/yaml/auxiliary/block_content.rs` → `4`; `grep -n 'fn parent_headers' crates/biome_yaml_formatter/src/yaml/auxiliary/block_content.rs` → `301:`; `grep -n 'YamlBlockKeepIndicator' crates/biome_yaml_formatter/src/yaml/auxiliary/block_content.rs` → `313:`; `grep -c 'piece.is_newline()' crates/biome_yaml_formatter/src/yaml/auxiliary/block_content.rs` → `3`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"FormatYamlBlockContent block content value token","limit":3,"detail":"ids"}'
```
→ resolves `biome.crates.biome_yaml_formatter.src.yaml.auxiliary.block_content.FormatYamlBlockContent.fmt_fields` (:22-229) rank-1 line-exact (audited live 2026-08-24); coverage stdin-JSON on the path: no_recorded_issue / metadata_match / generation_matches=true.

---
**Verdict:** ADOPT the stats+matrix as the reference algorithm for block-scalar reformatting; the Keep-chomping ownership chain (next-token trivia recovery, last-document self-break, comment suppression) is the part porters get wrong. This is the OTHER half of `yaml-formatter-utils.md`'s `ends_in_keep_chomped_scalar` — read both together when porting chomping semantics.
