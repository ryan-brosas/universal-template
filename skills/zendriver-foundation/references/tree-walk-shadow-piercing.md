<!-- capsule-v2 -->
# tree-walk-shadow-piercing — filter_recurse(_all): the one traversal every finder and parent/child lookup builds on

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** How do queries see inside shadow roots, and what does Element.parent/children actually cost?

## Shadow roots traversed FIRST, before children
**Path/Symbol:** `zendriver/core/util.py:filter_recurse_all` (:139-162), `filter_recurse` (:165-191), `html_from_tree` (:242-261); consumers `Element.parent` (:343-357) / `Element.children` (:359-389).
**Signature:** `def filter_recurse_all(doc: T, predicate) -> List[T]`; `def filter_recurse(doc, predicate) -> node | None`.
**Data Shape:** operates on any object with `.children` (raises TypeError otherwise); recurses into `child.shadow_roots[0]` then the child itself.

### Decisive source
```python
for child in doc.children:
    if predicate(child):
        out.append(child)
    if child.shadow_roots is not None:
        out.extend(filter_recurse_all(child.shadow_roots[0], predicate))
    out.extend(filter_recurse_all(child, predicate))
```
(first-match variant returns early through the same order). Parent lookup is a fresh walk:
```python
parent_node = util.filter_recurse(self.tree, lambda n: n.node_id == self.parent_id)
```

**Flow:** because CDP delivers the whole tree with shadow roots inline (`get_document(-1, True)` pierces them), all matching is *client-side*: query_selector/find map returned node ids back onto this cached tree instead of re-fetching. `children` special-cases IFRAME — real kids live under `.content_document` and cross-origin frames yield an empty list. `parent` raises RuntimeError when no tree was supplied (factory `create(node, tab)` without `tree`), which is why finders always pass the shared doc.
**Invariant:** shadow-root recursion happens BEFORE child recursion and only into `shadow_roots[0]` (first root only) — reordering changes match precedence; dropping the `[0]` breaks on multi-root hosts. And `parent`/`children` are O(tree) walks per access, not cached edges.
**Probe:** direct tests pin iframe piercing (`tests/core/test_tab.py::test_query_selector_all_include_frames_queries_nested_iframe_documents`, :95); static anchor at pin: `grep -c 'shadow_roots' zendriver/core/cloudflare.py` shows the solver building on the same pierced doc.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "filter_recurse shadow_roots", limit: 5 });
```

## Verdict
Adopt the client-side id-mapping + pierced-tree design wholesale (it is zendriver's performance model); adapt the iframe branch to your frame policy; cache parents if you call `.parent` in loops — the source does not.
