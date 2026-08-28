<!-- capsule-v2 -->
# Dual predicate surface — how do you let the SAME traversal API accept both serializable dict queries and ad-hoc lambdas?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255` (pydantic_evals); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter exposing tree-search over recorded spans must serve two masters: production evaluators that need PERSISTABLE, diffable query objects (dicts), and tests/debugging that want ad-hoc lambdas. How do you keep one traversal surface for both without duplicating find/first/any per kind?

## One generator per direction; callable short-circuit at the match boundary
**Path/Symbol:** `pydantic_evals/pydantic_evals/otel/span_tree.py:SpanNode.matches` (:252-257), `SpanPredicate` (:464), node traversals `find_children/first_child/any_child` (:169-182) / `find_descendants/first_descendant/any_descendant` (:187-203) / `find_ancestors/first_ancestor/any_ancestor` (:220-236); tree-level `SpanTree.find/first/any` (:517-527) + flat `__iter__` (:534-536).
**Signature:** `matches(self, query: SpanQuery | SpanPredicate) -> bool`; `SpanPredicate = Callable[[SpanNode], bool]`; every traversal takes `predicate: SpanQuery | SpanPredicate`.
**Data Shape:** `SpanQuery` is a `TypedDict(total=False)` — a plain JSON-serializable dict; `SpanPredicate` is a bare callable. The union is accepted at EVERY entry point, resolved exactly once inside `matches`.

### Decisive source
```python
def matches(self, query: SpanQuery | SpanPredicate) -> bool:
    """Check if the span matches the query conditions or predicate."""
    if callable(query):
        return query(self)

    return self._matches_query(query)
```

**Flow:** every `_filter_*` generator (children/descendants/ancestors/tree-flat) yields nodes whose `matches(predicate)` is true; `find_*` = `list(gen)`, `first_*` = `next(gen, None)`, `any_*` = `first_* is not None`. The callable check happens at the single match boundary, so lambdas never touch the dict evaluator and dicts never get called. Tree-level `find/first/any` iterate the FLAT `nodes_by_id` (start-time order), while node-level methods walk structure — same predicate type, different scope.
**Invariant:** the serializable form and the ad-hoc form must be INTERCHANGEABLE at every call site — that is only true if dispatch happens once, at `matches`, not at each traversal wrapper. Adding a new traversal direction means one `_filter_*` generator plus three thin wrappers, never a second predicate kind.
**Probe:** `tests/evals/test_otel.py::test_matches_function_directly` (:837-871) exercises lambda predicates on the same surface as dict queries; `test_span_tree_find_all` (:126-140) + `test_span_tree_any` (:141-151) pin tree-level find/any with lambdas; `test_span_query_basics` (:605-640) pins the dict form on the identical API. Suite EXECUTED GREEN at pin this pass (29 passed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "SpanNode matches SpanPredicate find first any", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session (stdio env reference unavailable at transport open); anchors confirmed by direct read of span_tree.py :169-257/:464/:517-536 at pin `a5b5fb7a` (zero drift, clean tree).

## Verdict
Adopt the dual-surface pattern verbatim for ANY search API that must serve both persisted queries and interactive predicates: one `XQuery | XPredicate` union, one dispatch point (`if callable(...)`), one generator per traversal direction with list/next/is-not-None wrappers. Adapt the TypedDict vocabulary to your domain; omit the dict evaluator entirely if you never need persistable queries (then drop the union). Coverage caveat: none — span_tree.py read whole this pass.
