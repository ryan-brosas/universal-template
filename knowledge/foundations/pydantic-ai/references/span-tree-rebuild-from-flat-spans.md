<!-- capsule-v2 -->
# Span-tree rebuild from flat spans — how do you turn an unordered batch of finished OTel spans into a parent/child tree without losing subtrees when parents are missing?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255` (pydantic_evals); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter building assertions over recorded traces receives a FLAT list of finished spans (no order guarantee, possibly partial — parents dropped by sampling or export). How do you link them into a tree whose child/roots ordering is deterministic and whose partial captures degrade gracefully?

## Rebuild-from-scratch with start-time sort, orphan-tolerant root election
**Path/Symbol:** `pydantic_evals/pydantic_evals/otel/span_tree.py:SpanTree._rebuild_tree` (:492-512), `add_spans` (:483-490), `SpanNode.from_readable_span` (:140-155), `SpanNode.add_child` (:157-164).
**Signature:** `_rebuild_tree(self) -> None`; `add_spans(spans: list[SpanNode]) -> None`; `from_readable_span(span: ReadableSpan) -> SpanNode` (static).
**Data Shape:** `SpanTree.nodes_by_id: dict[str, SpanNode]` keyed by `node_key = f'{trace_id:032x}:{span_id:016x}'`; `roots: list[SpanNode]` derived; node back-references (`parent`, `children_by_id`) are `__post_init__` state, not dataclass fields.

### Decisive source
```python
def _rebuild_tree(self):
    # Ensure spans are ordered by start_timestamp so that roots and children end up in the right order
    nodes = list(self.nodes_by_id.values())
    nodes.sort(key=lambda node: node.start_timestamp or datetime.min)
    self.nodes_by_id = {node.node_key: node for node in nodes}

    # Build the parent/child relationships
    for node in self.nodes_by_id.values():
        parent_node_key = node.parent_node_key
        if parent_node_key is not None:
            parent_node = self.nodes_by_id.get(parent_node_key)
            if parent_node is not None:
                parent_node.add_child(node)

    # Determine the roots
    # A node is a "root" if its parent is None or if its parent's span_id is not in the current set of spans.
    self.roots = []
    for node in self.nodes_by_id.values():
        parent_node_key = node.parent_node_key
        if parent_node_key is None or parent_node_key not in self.nodes_by_id:
            self.roots.append(node)
```

**Flow:** `add_spans` merges into `nodes_by_id` then ALWAYS rebuilds from scratch (no incremental link/unlink). Step 1 sorts by `start_timestamp` (fallback `datetime.min`) and re-keys the dict so insertion order IS chronological — this alone fixes both `children` list order and `roots` order. Step 2 links each node to its looked-up parent; a node whose parent key is absent is simply not linked. Step 3 elects roots as nodes with no parent id OR a parent id missing from the batch — a dropped parent degrades to an extra root, never to a lost subtree. `from_readable_span` converts ns timestamps via `start_time / 1e9` to UTC datetimes and maps the OTel status enum NAME ('ERROR'→'error', 'OK'→'ok', else 'unset'); `add_child` asserts trace-id equality AND parent-span-id equality before linking.
**Invariant:** three rules: (1) sort BEFORE linking — dict insertion order is the only ordering source for children/roots, and OTel gives no order on finished-span batches; (2) orphan tolerance is deliberate — partial captures must add roots, not drop subtrees; (3) mis-parented or cross-trace spans crash LOUDLY at build time via the `add_child` asserts, never silently mis-link.
**Probe:** `tests/evals/test_otel.py::test_span_tree_flattened` (:116-124) pins flat iteration == start-time order (`['root', 'child1', 'grandchild1', 'grandchild2', 'child2', 'grandchild3']`); `test_span_node_status_captured` (:992-1010) pins the unset/ok/error mapping from real OTel spans; `test_context_subtree_concurrent` (:35-113) pins disjoint trees per async context. Suite EXECUTED GREEN at pin this pass (29 passed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "SpanTree _rebuild_tree add_spans from_readable_span", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session (stdio env reference unavailable at transport open); anchors confirmed by direct read of span_tree.py :140-164/:483-512 at pin `a5b5fb7a` (zero drift, clean tree).

## Verdict
Adopt rebuild-from-scratch + start-time-sort-before-link + orphan-tolerant root election verbatim for ANY flat-record→tree assembly (traces, event logs, dependency graphs): it is what makes partial captures safe and ordering deterministic. Adopt the loud build-time asserts for identity mismatches. Adapt the key format (`trace:span` hex) to your record ids; omit the ReadableSpan conversion if your records already carry typed timestamps/status. Coverage caveat: none — span_tree.py read whole this pass.
