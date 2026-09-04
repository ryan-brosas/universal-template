<!-- capsule-v2 -->
# YAML formatter utils — property reordering, keep-chomping end detection, and the literal-break multiline key trick

**Source:** biome MIT `main@6f7774dc` (drift plane pass 13); Codebase Memory `biome`. **Question:** Which YAML-specific formatting invariants live outside per-node rules, and what does each preserve?

## FormatProperties: tags before anchors, source order otherwise (utils.rs)
**Path/Symbol:** `crates/biome_yaml_formatter/src/utils.rs:21-83` (`FormatProperties` + `own`/`with_first_key`).
**Signature:** `own(properties, skip)` for flow nodes; `with_first_key(properties, from_first_key)` for block nodes — the parser attaches the block mapping's leading properties to its FIRST KEY node, and this iterator splices `take(count)` of them back (:57-64).
**Invariant:** Output order is ALL tags then ALL anchors (`tags.chain(anchors)`, :79-81), each group in source order — NOT strict source order. The skip/from_first_key split exists because properties can belong to the enclosing mapping; a porter printing a node's property list wholesale double-prints the mapping's anchor.

## lines_before_through_end_tokens (:85-113)
**Flow:** count newlines in leading trivia walking BACK through zero-width END tokens (MAPPING_END, FLOW_END…) because breaks land on those tokens' trivia; STOP at a comment ("whose own leading breaks belong to it").
**Probe:** `grep -n 'walks through those tokens' crates/biome_yaml_formatter/src/utils.rs` → `89:`.

## ends_in_keep_chomped_scalar (:115-131)
**Invariant:** If the document's last node is a `|+`/`>+` block scalar, IT owns every following break; enclosing collections must print none. Detection = walk to last leaf, then check ancestors for a BlockScalar header containing `YamlBlockKeepIndicator`. Missing this duplicates trailing blank lines.

## FormatMultilineKeyEntry: explicit `? key : value` with literal breaks (:146-225)
**Path/Symbol:** `crates/biome_yaml_formatter/src/utils.rs:135-144` (`multiline_plain_key`: only unqualified flow-yaml nodes whose value token contains `\n|\r`), `:186-206` (four-space return after `{ ? `), `:209-217` (two-space `:` alignment).
### Decisive source
```rust
// :155-158 doc — literal breaks are load-bearing
/// The line breaks are literal so that they don't expand the enclosing flow
/// collection, which stays on one line; a literal break resets the printer to
/// the document root, so the continuation and `:` lines carry their own
/// indentation.
```
**Invariant:** Key text written as raw `text()` NOT via node rules ⇒ suppression-comment checks must be done BY HAND (`mark_suppression_checked` loop :177-179). Synthesized `?` printed as text when token absent (:183).
**Probes:** `grep -c 'literal_line_break_without_parent' crates/biome_yaml_formatter/src/utils.rs` → `2`; `grep -n 'needs_space_before_colon' crates/biome_yaml_formatter/src/utils.rs` → `12:`; `grep -n 'YamlBlockKeepIndicator' crates/biome_yaml_formatter/src/utils.rs` → `128:`; `grep -c '#\[test\]' crates/biome_yaml_parser/src/lexer/tests/block.rs` ≥ 20 (lexer suite backs these semantics).

**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"FormatProperties ends_in_keep_chomped_scalar multiline key","limit":5,"detail":"ids"}'
```

---
**Verdict:** ADOPT all four helpers as a unit; they encode YAML's ownership rules (properties→mappings, breaks→chomped scalars, keys→explicit entries).
