<!-- capsule-v2 -->
# Range-format comment re-anchoring — how can a placement rule pick a node that isn't printed, and what must happen then?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** when only a slice of the document is formatted (range/on-type formatting), a placement rule may resolve to an ancestor OUTSIDE the formatted subtree — where does the comment go so it is not silently lost?

## The re-anchor seam
**Path/Symbol:** `crates/biome_formatter/src/comments/builder.rs` — `normalize_placement_into_formatted_tree` (:329-381); the pre-placement shortcut in `flush_comments` (:283-312); list-as-root push in `visit` (:74-82).
**Signature:** `fn normalize_placement_into_formatted_tree(root: &Option<SyntaxNode<L>>, placement: CommentPlacement<L>) -> CommentPlacement<L>`.
**Data Shape:** input = any explicit Leading/Trailing/Dangling placement; test = `!node.ancestors().any(|a| &a == root)`; output = same kind of placement but anchored on `root` (or root's first/last child when root IS a list).

### Decisive source
```rust
// builder.rs:337-377 — comments attach ONLY to nodes the formatter visits;
// anything anchored outside the formatted tree is moved onto the tree itself:
CommentPlacement::Leading { node, comment }
| CommentPlacement::Trailing { node, comment }
| CommentPlacement::Dangling { node, comment }
    if !node.ancestors().any(|ancestor| &ancestor == root) =>
{
    debug_assert!(
        comment_range.end() <= root_content.start()
            || comment_range.start() >= root_content.end(),
        "A comment inside of the formatted tree was placed on a node outside of it. ...");
    if comment_range.start() >= root_content.end() {
        let anchor = if root.kind().is_list() { root.last_child() } else { Some(root.clone()) };
        ... trailing(anchor) / dangling(root)
    } else {
        // symmetric leading(first_child / root) path
    }
}
```
**Flow:** two defenses. (1) In `flush_comments`, any pending comment whose text ends before `root_content_start` (before the formatted subtree's first token) skips placement rules entirely and becomes a LEADING comment of the root — rules would otherwise see out-of-subtree context (:296-305; lists exempted because they never print their own comments). (2) After `place_comment` returns, the normalizer re-anchors placements whose target is not a root-ancestor: comment after the tree ⇒ trailing on root/last-child; before ⇒ leading on root/first-child; empty-list anchors fall back to dangling. The doc example: formatting just `continue;` inside `for (;;) continue; /* a */` — the rule picks the `for` loop, which won't be printed, so the comment lands back on the continue statement.
**Invariant:** every comment must end up attached to a node the formatter actually visits — a placement onto any non-printed node LOSES the comment silently. The debug_assert encodes that only edge comments can legitimately be outside; an INNER comment placed outside means a broken language rule, not something to paper over.
**Probe:** builder.rs tests — `sub_tree_root_leading_comments` :1183-1199 (pre-first-token comment bypasses rules straight to root.leading), `list_root_leading_comments` :1204-1222 (list root delegates to first child), `parentless_root_leading_comments` :1227-1238 (full-document root keeps normal placement), plus `r_paren` :963-1087 exercising source-map-driven re-anchoring.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "normalize_placement_into_formatted_tree", limit: 5, fields: ["signature", "name", "file"] });
// CommentsBuilderVisitor.normalize_placement_into_formatted_tree builder.rs 329-381 (line-exact)
```

## Verdict
Adopt both defenses for ANY range/on-type formatting feature — without them every partially-formatted file drops edge comments; adapt the ancestor check to your tree API; omit the list special-casing if your IR has no list nodes. Coverage caveat: the debug_assert branch (inner-comment-outside) has no direct test.
