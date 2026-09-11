<!-- capsule-v2 -->
# Separated-list sort & split — how do you reorder `a, b, c` AST lists without losing separators, comments, or trailing-comma shape?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** sorting members/imports/keys means moving nodes BETWEEN separators — what chunking and separator-repair rules keep the tree lossless?

## The list-utils seam
**Path/Symbol:** `crates/biome_analyze/src/utils.rs` — `is_separated_list_sorted_by` (:13-43), `sorted_separated_list_by` (:53-108), `fix_separators` (:122-161), `split_separated_list` (:174-233), `count_lines_in_file` (:240-264); `shared/sort_attributes.rs` — `SortableAttribute` comparators + whitespace-gap fixer (:5-111); `shared/class_dedup.rs` — `find_duplicate_classes` (:87-172).
**Signature:** `fn sorted_separated_list_by<L, List, Node, Key>(list: &List, get_key: impl Fn(&Node) -> Option<Key>, make_separator: fn() -> SyntaxToken<L>, comparator: impl Fn(&Key,&Key) -> Ordering) -> Result<List, SyntaxError>`.
**Data Shape:** elements collected as `(Option<Key>, Node, Option<SyntaxToken> trailing_separator)`; buggy nodes or separators abort with `SyntaxError` (never silently skipped).

### Decisive source
```rust
// utils.rs:76-89 — keyless nodes are CHUNK DELIMITERS: split_mut on key.is_none()
// sorts each run independently; last_has_separator captured BEFORE the in-place sort:
for slice in elements.split_mut(|(key, _, _)| key.is_none()) {
    let last_has_separator = slice.last().is_some_and(|(_, _, sep)| sep.is_some());
    slice.sort_by(|(key1, _, _), (key2, _, _)| match (key1, key2) {
        (Some(k1), Some(k2)) => comparator(k1, k2),
        (Some(_), None) => Ordering::Greater,   // keyed before unkeyed within a chunk tail
        (None, Some(_)) => Ordering::Less,
        (None, None) => Ordering::Equal,
    });
    fix_separators(slice.iter_mut().map(|(_, node, sep)| (node, sep)),
                   last_has_separator, make_separator);
}
```
```rust
// utils.rs:130-158 — separator repair: drop an unneeded LAST separator only when it
// has no attached comments (transferring its trivia onto the node); CREATE a missing
// one from node's trailing trivia (trim_trailing_trivia_pieces):
if i == last_index && !(needs_last_separator
    || separator.has_leading_comments() || separator.has_trailing_comments())
{ /* transfer trivia, *optional_separator = None */ }
else if i != last_index || needs_last_separator {
    *optional_separator = Some(match node.syntax().last_trailing_trivia() {
        Some(trivia) => make_separator()
            .append_trivia_pieces(trim_trailing_trivia_pieces(trivia.pieces())),
        _ => make_separator(),
    });
}
```
**Flow:** rebuild via odd/even interleave into `SyntaxNode::new_detached(kind, ...)` (items at even indices, separators at odd). `is_separated_list_sorted_by` mirrors the same chunking WITHOUT early return so a later SyntaxError still surfaces ("We don't return early because we want to return the error if we met one", :32-34 comment). Attribute sorting adds a cross-attribute whitespace guarantee: if neither neighbor ends/starts with whitespace, rewrite the left node's last token to gain a trailing space (`get_sorted_attributes` :73-103). Class dedup keeps FIRST occurrences and preserves each kept token's original prefix whitespace (`prefix_start..text_end` slicing), reporting duplicates in first-duplicate-seen order.
**Invariant:** comments anchored to a separator PIN that separator (never removed); a moved node's trailing trivia must migrate to the new separator or be trimmed deliberately; sorting is stable inside chunks; keyless nodes never move across their chunk boundary.
**Probe:** upstream consumers pin behavior: `use_sorted_attributes` / `noDuplicateClasses` spec fixtures under biome_js/css_analyze tests exercise these helpers through rule snapshots; class_dedup carries doctests (`foo bar foo` → `"foo bar"`, leading-whitespace preservation :72-86) executed as part of `cargo test --doc`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "sorted_separated_list_by fix_separators split_separated_list", limit: 10, fields: ["signature", "name", "file"] });
// sorted_separated_list_by utils.rs 53-108; fix_separators 122-161 (line-exact)
```

## Verdict
Adopt keyless-chunk splitting, comment-aware separator repair with trivia transfer, stable sorts, and first-wins dedup with whitespace preservation; adapt the key type and comparator per rule; omit count_lines_in_file unless porting noExcessiveLinesPerFile. Coverage caveat: pinned by consumer-rule fixtures + doctests, no direct unit test for fix_separators.
