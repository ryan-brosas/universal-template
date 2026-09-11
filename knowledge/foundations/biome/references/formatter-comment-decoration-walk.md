<!-- capsule-v2 -->
# Comment decoration walk — how are source comments classified into enclosing/preceding/following context before any placement decision?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** a porting formatter must reproduce how every comment gets its surrounding-node context (`DecoratedComment`) from one linear tree walk — what is the state machine, and why do lists get special treatment?

## The decorate seam
**Path/Symbol:** `crates/biome_formatter/src/comments/builder.rs` — `CommentsBuilderVisitor` state (:14-34), `visit_node` Enter/Leave (:131-168), `visit_token` (:170-237), `enclosing_node()` index resolution (:239-247), `update_comments` (:261-281).
**Signature:** `fn visit(self, root: &SyntaxNode<L>) -> (CommentsMap<SyntaxElementKey, SourceComment<L>>, FxHashSet<SyntaxElementKey>)`.
**Data Shape:** visitor fields: `pending_comments: Vec<DecoratedComment>` (queue), `preceding_node: Option<SyntaxNode>` (set on Leave), `following_node_index: Option<usize>` (index into `parents`, set on first-child Enter, cleared after first token / on Leave), `parents: Vec<SyntaxNode>` stack of non-list ancestors, `last_token`, plus subtree-root bookkeeping (`is_sub_tree`, `is_list_root`, `root_content_start`). `DecoratedComment { enclosing, preceding, following, following_token, text_position, lines_before, lines_after, piece, kind }`.

### Decisive source
```rust
// visit_node Enter — the enclosing-node trick: while walking toward the first
// child node, that child is recorded as "following"; everything seen between
// two children is enclosed by parents[following_node_index - 1]:
let is_root = matches!(self.following_node_index, Some(0));
if self.following_node_index.is_none() || is_root {
    self.flush_comments(Some(&node));          // flush pending w/ following = this node
    self.following_node_index = Some(self.parents.len());
}
self.parents.push(node);
// ... Leave: pop, following_node_index = None, flush again,
//     self.preceding_node = Some(node);
```
**Flow:** preorder-with-tokens walk. Enter(node): skip lists entirely; if no `following_node_index` yet, flush pendings with `following = node` and record the index. Enter(token): first drain last token's trailing trivia via `visit_trailing_comments` (SameLine until a newline flips position to OwnLine and freezes `trailing_end`), then scan leading trivia queueing comments with `following_token = token`; finally `update_comments` back-patches `lines_after` of all pendings from the NEXT comment's `lines_before`. Leave(node): pop, clear following, flush (now-orphaned pendings get `following = None` → they become trailing/dangling), set `preceding_node = node`. After the loop, the final `last_token`'s trailing comments are flushed against the root, then a final flush. Lists never appear on `parents` EXCEPT when the formatted root itself is a list (range/on-type formatting): then the list is pushed so inter-child comments enclose it instead of the next sibling's child (:74-82). `assert!(parents.is_empty())` after the walk is the structural sanity gate.
**Invariant:** a comment's `enclosing` must be the closest non-list ancestor that fully contains it, `preceding`/`following` must be non-list DIRECT children of `enclosing`, and `lines_after` of comment N equals `lines_before` of comment N+1 (or the next token's count). Porters who push lists onto the stack unconditionally misattribute every inter-element comment to the list instead of the following element; porters who forget the post-loop `last_token` flush silently drop trailing comments in range-format mode.
**Probe:** `crates/biome_formatter/src/comments/builder.rs` test mod — `leading_comment` (:787-828: OwnLine comment inside object expression lands leading on `b`, enclosing JS_OBJECT_EXPRESSION), `trailing_comment` (:831-871), `end_of_line_comment` (:874-914), `list_as_sub_tree_root` (:1153-1178: enclosing IS the statement list, siblings resolve through `.parent()`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "CommentsBuilderVisitor visit_trailing_comments", limit: 10, fields: ["signature", "name", "file"] });
// CommentsBuilderVisitor.visit_trailing_comments builder.rs 383-447 (line-exact)
```

## Verdict
Adopt the decorate-then-place split (context decoration is language-independent; only `place_comment` is per-language); adapt the AST kinds/list predicate; omit the source-map parenthesis recovery unless you also remove parentheses in an AST transform (that half is its own capsule). Coverage caveat: decoration semantics beyond the six unit tests rest on source reading.
