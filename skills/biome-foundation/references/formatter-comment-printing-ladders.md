<!-- capsule-v2 -->
# Leading/trailing/dangling comment printing ladders — which separator follows each comment, and when does a trailing comment become a line suffix?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** given the classified `SourceComment` lists, what exact space/break/empty-line decisions print them — and what preserves blank-line fidelity and JSDoc overload nestling?

## The printing seam
**Path/Symbol:** `crates/biome_formatter/src/trivia.rs` — `fmt_leading_comments_on_lines` (:241-281), `LeadingCommentLayout::fmt` + content-after-last-comment (:174-237), `FormatTrailingComments::fmt` (:323-406), dangling trio with `DanglingIndentMode` Block|Soft|None and InlineComments layout (:409-660), `should_nestle_adjacent_doc_comments` (:29-41).
**Signature:** `format_leading_comments(node)` / `..._from_slice(&[SourceComment])`; trailing/dangling equivalents; builders `.with_following_content(content)` / `.with_indented_following_content(content)` / `.with_block_indent()` / `.with_soft_block_indent()`.
**Data Shape:** decision input per comment = `(kind: Line|Block|InlineBlock, lines_before, lines_after, previous comment kind)`; outputs are the IR separators `space / soft_line_break_or_space / hard_line_break / empty_line` plus `line_suffix + expand_parent`.

### Decisive source
```rust
// trivia.rs:254-275 — the leading ladder: block comments keep same-line runs
// together, 0/1/2+ lines_after map to space/hard-break/empty-line; line
// comments always break (they cannot be followed by code on their line):
CommentKind::Block | CommentKind::InlineBlock => match comment.lines_after() {
    0 => { /* maybe_space(!nestle) */ }
    1 => {
        if comment.lines_before() == 0 { write!(f, [soft_line_break_or_space()])?; }
        else                          { write!(f, [hard_line_break()])?; }
    }
    _ => write!(f, [empty_line()])?,
},
CommentKind::Line => match comment.lines_after() {
    0 | 1 => write!(f, [hard_line_break()])?,
    _ => write!(f, [empty_line()])?,
},
```
**Flow:** leading = print each comment then ladder on its `lines_after`; between last comment and content, Line ⇒ hard break, Block ⇒ soft-or-space (indented variant wraps content in `indent`). Trailing: accumulate `total_lines_before` — any accumulated line breaks convert the remainder into `line_suffix(...)` + `expand_parent` (own-line trailing comments ride the enclosing group's break); inside a suffix, 0/1/2+ `lines_before` map to (space-after-block-but-hard-after-Line | hard | empty); SameLine block trailing prints inline with `maybe_space`, SameLine LINE trailing still goes to a suffix because it would otherwise eat following tokens. Dangling: Multiline layout puts a hard break before every non-first comment; Soft mode appends a final hard break iff the last dangling is a Line comment (guarantees the closer lands on its own line); InlineComments keeps `(/* one */ /* two */)` on one line but falls back whenever ANY comment is a Line (`can_keep_dangling_comments_inline`). Nestling: two adjacent multiline doc comments with ZERO characters between them stay glued (`maybe_space(false)` / no separator) — this is how JSDoc overload sets survive formatting.
**Invariant:** blank-line preservation is exactly `_ => empty_line()` for ≥2 source breaks — collapsing or inventing blank lines around comments is the most-visible porting defect. The nestle predicate requires BOTH pieces multiline AND byte-adjacent (`second.start − first.end == 0`) AND both doc-shaped; relaxing adjacency merges unrelated comments.
**Probe:** `crates/biome_js_formatter/tests/specs/js/module/comments.js` + `.snap` (:25-31 source vs snap :38-40/:126-128 — `/** something **/` placement across argument positions pins both ladders end-to-end through the real formatter). Nestle rule itself has no dedicated fixture in-tree (its Prettier-parity rationale is cited at trivia.rs :26-28) — recorded as an honesty note.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "should_nestle_adjacent_doc_comments format_trailing_comments", limit: 10, fields: ["signature", "name", "file"] });
// should_nestle_adjacent_doc_comments trivia.rs 29-41 (line-exact)
```

## Verdict
Adopt all four ladders as-is — they encode prettier-observable output; adapt separator vocabulary to your IR; omit InlineComments if your grammar never allows adjacent inline blocks. Coverage caveat: nestling is pinned only indirectly via upstream Prettier parity tests.
