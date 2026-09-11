<!-- capsule-v2 -->
# Default comment placement matrix — which node owns a comment when the language's `place_comment` has no opinion?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** what is the exact leading/trailing/dangling decision table that runs for every comment a language's `CommentStyle::place_comment` returns `Default` for — and where does the SameLine trailing rule diverge from the naive "attach to preceding"?

## The placement seam
**Path/Symbol:** `crates/biome_formatter/src/comments/builder.rs` — `CommentsBuilder::add_comment` Default arm (:513-595); taxonomy and heuristic docs in `crates/biome_formatter/src/comments.rs` (:472-720, `CommentTextPosition`, `CommentPlacement::Default` doc).
**Signature:** `fn add_comment(&mut self, placement: CommentPlacement<L>)` — explicit Leading/Trailing/Dangling variants bypass the matrix; `Default(decorated)` enters it.
**Data Shape:** key = `(text_position: EndOfLine|OwnLine|SameLine, preceding: Option<node>, following: Option<node>)` → action = push onto preceding (trailing), following (leading), or enclosing (dangling).

### Decisive source
```rust
// builder.rs:563-579 — SameLine with BOTH nodes present: trailing ONLY if the
// comment's piece ends exactly at the preceding node's end (no token between);
// otherwise it belongs to the following node. This one comparison is what makes
// `a /* c */ b` trail on `a` but `a, /* c */ b` lead on `b`:
(Some(preceding), Some(following)) => {
    if preceding.text_range_with_trivia().end()
        == comment.piece().as_piece().token().text_range().end()
    {
        self.push_trailing_comment(&preceding, comment);
    } else {
        self.push_leading_comment(&following, comment);
    }
}
```
**Flow:** EndOfLine (same line as previous token, break before next): both-nodes ⇒ TRAILING on preceding (a line break separates it from following); preceding-only ⇒ trailing; following-only ⇒ leading; none ⇒ dangling. OwnLine (break before AND after): FOLLOWING WINS — any following node takes the comment as leading (:540-551); else trailing on preceding; else dangling. SameLine: as excerpted — adjacency-compared trailing, else leading; single-sided cases mirror EndOfLine; none ⇒ dangling. `take_preceding_node()`/`take_following_node()` consume each side so every branch is exactly once.
**Invariant:** the matrix must be total over 3×4 combinations and must prefer, for OwnLine comments, the FOLLOWING node — porting an OwnLine rule that trails on the preceding node moves every standalone comment above a statement to below its predecessor (the classic prettier-family porting bug). The SameLine equality compares against the comment PIECE's token end — using `preceding.text_trimmed_range().end()` instead misclassifies comments separated by trivia.
**Probe:** builder.rs tests pin all three positions against real JS parses — `leading_comment` :787-828 (OwnLine→leading on `b`), `trailing_comment` :831-871 (SameLine adjacent→trailing on `a`), `end_of_line_comment` :874-914 (EndOfLine→trailing on `a`); `comments.rs` doc examples (:569-711) enumerate each ladder rung.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "CommentsBuilder add_comment CommentTextPosition EndOfLine OwnLine", limit: 10, fields: ["signature", "name", "file"] });
// CommentsBuilder.add_comment builder.rs 502-597 (line-exact)
```

## Verdict
Adopt the whole matrix verbatim — it is language-independent and encodes prettier-compatible expectations; adapt node types; omit nothing here except in languages whose syntax forbids dangling comments entirely. Coverage caveat: only the three canonical positions have direct tests; the both-nodes-SameLine-with-token case rests on source + doc-comment examples.
