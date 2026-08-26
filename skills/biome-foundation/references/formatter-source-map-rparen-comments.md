<!-- capsule-v2 -->
# Source-map r_paren comment recovery — where do comments go when a transform deleted the parentheses that enclosed them?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** after an AST transform removes `(...)` and moves its trivia onto an identifier, how does the formatter still attribute comments that sat inside the now-deleted parens to the right node?

## The paren-recovery seam
**Path/Symbol:** `crates/biome_formatter/src/comments/builder.rs` — `SourceParentheses` (:642-763), trigger in `visit_trailing_comments` (:426-443), `flush_before_r_paren_comments` (:451-493).
**Signature:** `fn r_paren_source_range(&mut self, offset: TextSize) -> Option<TextRange>` (monotonic offsets required); `fn outer_most_parenthesized_node(&self, token, parens_source_range) -> SyntaxNode<L>`.
**Data Shape:** `SourceParentheses::Empty | SourceMap { map: &TransformSourceMap, next: Option<DeletedRangeEntry>, tail: DeletedRanges }` — a single-pass cursor over deleted source ranges; recovery rewrites `preceding`/`enclosing` of already-queued comments.

### Decisive source
```rust
// builder.rs:715-729 — the ancestor search is two-phase because MANY nodes can
// end exactly at the deleted ")"; start-tracking picks the outermost one that
// also starts at the same position:
// We first find the closest node that directly ends at the position of the
// right paren. We then continue upwards to find the most outer node that
// starts at the same position as that node.
let mut start_offset = None;
let ancestors = token.ancestors().take_while(|node| {
    if node.kind().is_list() { return false; }
    if let Some(start) = start_offset {
        TextRange::new(start, r_paren_source_end).contains_range(source_range)
    } else if source_range.end() >= r_paren_source_end {
        start_offset = Some(source_range.start());
        true
    } else {
        source_range.end() < r_paren_source_end
    }
});
```
**Flow:** while scanning trailing trivia, each piece offset is checked against the deleted-range cursor; hitting a former `)` (found via `range.text.find(')')` inside the deleted text) triggers the #[cold] flusher: every pending comment from `comments_start` gets `preceding = outer_most_parenthesized_node(...)`, `enclosing = its parent`, EndOfLine demotion for post-newline trailing comments, then immediate flush. The take_while walk: first find the innermost ancestor whose transformed range ends at/after the r-paren end, record its start, then keep climbing while ranges stay CONTAINED in `(start, r_paren_source_end)` — yielding e.g. ReferenceIdentifier→IdentifierExpression for `!(a /* c */)` after paren removal (:718-729 comment). Lists terminate the walk (`return false`) but the token's parent always passes, so `.last().unwrap()` is safe.
**Invariant:** offsets must arrive in increasing order (single forward cursor — no rescans); the enclosing used is `preceding.parent()` so the comment's enclosure matches the new (paren-free) tree shape. Porters who pick the INNERMOST ending-at-rparen node attach the comment one level too deep; porters who skip the containment phase grab nodes starting before the whole expression.
**Probe:** builder.rs test `r_paren` :963-1087 — builds a real TransformSourceMap with both paren ranges deleted, performs the BatchMutation trivia move, and asserts the argument's comment becomes OwnLine/trailing on JS_IDENTIFIER_EXPRESSION under a JS_UNARY_EXPRESSION enclosure; `r_paren_inside_list` :1125-1148 pins the sequence-expression variant.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "flush_before_r_paren_comments SourceParentheses", limit: 5, fields: ["signature", "name", "file"] });
// CommentsBuilderVisitor.flush_before_r_paren_comments builder.rs 451-493 (line-exact)
```

## Verdict
Adopt ONLY if your pipeline deletes parentheses via AST mutation before formatting (suppression-style transforms); adapt the deleted-range store to your source map; omit entirely (keep `Empty`) for formatters that never remove syntax. Coverage caveat: behavior beyond the two direct tests is source-derived.
