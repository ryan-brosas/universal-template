<!-- capsule-v2 -->
# stop_recursing_when pruning — how do you bound recursion for related-span conditions without changing what counts as a descendant?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255` (pydantic_evals); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter adding "some_descendant_has" / "all_ancestors_have" style conditions to a tree query DSL needs a way to stop recursion at a boundary (e.g. "only within this subtree") — but must decide whether the boundary node itself is included, and whether pruning changes COUNT-based conditions or only WHICH nodes get checked.

## Boundary-included pruning, applied to quantifiers but not to counts
**Path/Symbol:** `pydantic_evals/pydantic_evals/otel/span_tree.py` `SpanQuery.stop_recursing_when` docstring (:73-75), `SpanNode._filter_descendants` (:205-215), `SpanNode._filter_ancestors` (:238-247), per-query `pruned_descendants`/`pruned_ancestors` locals (:351-355/:383-385).
**Signature:** `stop_recursing_when: SpanQuery` — a query-level field, SIBLING of the conditions it bounds (not nested inside them); also accepted as a direct parameter on `find_descendants`/`find_ancestors` and friends.
**Data Shape:** the stop condition is itself a full SpanQuery/predicate; evaluated per visited node via the same `matches` dispatch.

### Decisive source
```python
# _filter_descendants (:205-215)
stack = list(self.children)
while stack:
    node = stack.pop()
    if node.matches(predicate):
        yield node
    if stop_recursing_when is not None and node.matches(stop_recursing_when):
        continue                      # boundary node IS yielded, its children are NOT pushed
    stack.extend(node.children)

# _filter_ancestors (:238-247)
node = self.parent
while node:
    if node.matches(predicate):
        yield node
    if stop_recursing_when is not None and node.matches(stop_recursing_when):
        break                         # symmetric: boundary included, beyond excluded
    node = node.parent

# pruned locals used by the some/all/no quantifiers (:351-355)
@cache
def pruned_descendants():
    stop_recursing_when = query.get('stop_recursing_when')
    return (
        self._filter_descendants(lambda _: True, stop_recursing_when) if stop_recursing_when else descendants()
    )
```

**Flow:** in `_matches_query`, the some/all/no DESCENDANT and ANCESTOR quantifiers iterate the PRUNED collections when `stop_recursing_when` is present; the min/max descendant-count and min/max-depth guards iterate the UNPRUNED collections. So pruning changes which nodes the quantifiers check, never how many exist.
**Invariant:** three rules: (1) the boundary node is INCLUDED in both directions — "stop at level2" means level2 itself is visible, its subtree/above-it is not; yielding before the stop check is what makes this hold; (2) pruning is a QUERY-LEVEL field, so one stop condition bounds all related-span conditions in that query dict at once; (3) count-based conditions must stay unpruned — a user asking `min_descendant_count: 5` wants the true subtree size, not the pruned view.
**Probe:** `tests/evals/test_otel.py::test_span_tree_ancestors_methods` stop block (:465-474): `some_ancestor_has level1` FAILS with stop-at-level2 (level1 beyond boundary) while `all_ancestors_have level` PASSES with stop-at-level1 (boundary level1 included, root excluded); `test_span_tree_descendants_methods` stop block (:552-561): `some_descendant_has leaf` FAILS with stop-at-level2, `no_descendant_has leaf` PASSES with stop-at-level3. Suite EXECUTED GREEN at pin this pass (29 passed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "stop_recursing_when _filter_descendants pruned", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session (stdio env reference unavailable at transport open); anchors confirmed by direct read of span_tree.py :73-75/:205-215/:238-247/:351-355/:383-385 at pin `a5b5fb7a` (zero drift, clean tree).

## Verdict
Adopt yield-before-stop-check for boundary-included pruning in both traversal directions of any tree query DSL — it is the one-line choice that makes "stop at X" mean "X visible, beyond invisible" instead of silently dropping X. Adopt the split between pruned quantifier sets and unpruned count sets; adapt the field name; omit the feature entirely if your trees are shallow enough that unbounded recursion is cheap. Coverage caveat: none — span_tree.py read whole this pass.
