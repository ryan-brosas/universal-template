<!-- capsule-v2 -->
# Dependency graph substrate — what minimal contract must invalidation rely on when formulas declare dependencies lazily?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What is the smallest node/edge/relation model that lets a change to one column invalidate exactly the right rows of every dependent column, including across tables?

## Node/Edge/Relation graph with iterative BFS invalidation (depend.py)
**Path/Symbol:** `sandbox/grist/depend.py:Node` (:24–31), `Edge` (:34–43), `CircularRefError` (:46–50), ALL_ROWS sentinel (:53–60), `Graph.add_edge` (:84–92), `clear_dependencies` (:94–102), `reset_dependencies` (:104–111), `remove_node_if_unused` (:113–122), `invalidate_deps` (:124–164). Inspired-by note: ninja build system (:13–14).
**Signature:** `invalidate_deps(dirty_node, dirty_rows, recompute_map, include_self=True)`; `add_edge(out_node, in_node, relation)`; Edge = (out_node, in_node, relation) meaning out DEPENDS ON in.
**Data Shape:** Node = (table_id, col_id) namedtuple with empty __slots__; _all_edges: set of Edge; _in_node_map[node] gives dependents; _out_node_map[node] gives dependencies; recompute_map maps Node -> SortedSet|ALL_ROWS; relations implement get_affected_rows(rows), reset_rows(rows), reset_all().

### Decisive source
```python
    to_invalidate = [(dirty_node, dirty_rows)]
    while to_invalidate:
      dirty_node, dirty_rows = to_invalidate.pop()
      if include_self:
        if recompute_map.get(dirty_node) == ALL_ROWS:
          continue                                   # already fully invalidated
        if dirty_rows == ALL_ROWS:
          recompute_map[dirty_node] = ALL_ROWS
          # If all rows are being recomputed, clear the dependencies of the affected column.
          # (Dependencies are re-added during recomputing, but only from an empty set.)
          self.clear_dependencies(dirty_node)
        else:
          out_rows = recompute_map.setdefault(dirty_node, SortedSet())
          prev_count = len(out_rows)
          out_rows.update(dirty_rows)
          # Do not bother recursing into dependencies if nothing new was added.
          if len(out_rows) <= prev_count:
            continue
      include_self = True
      for edge in self._in_node_map.get(dirty_node, ()):
        affected_rows = edge.relation.get_affected_rows(dirty_rows)
        # Previously recursive; unrolled into this while loop after recursion errors
        to_invalidate.append((edge.out_node, affected_rows))
```

**Flow:** a data/formula change calls invalidate_deps with the dirty node+rows -> worklist pops entries; partial-row dirtiness MERGES into a SortedSet and propagates to dependents ONLY when new rows appeared (termination guarantee); ALL_ROWS dirtiness collapses the node to whole-column recompute AND clears its outgoing dependency edges because dependencies are rediscovered during re-evaluation; each edge maps rows through its Relation before forwarding (cross-table row identity lives entirely in relations, e.g. SingleRowsIdentityRelation) -> lookup-map nodes nobody consumes get dropped via remove_node_if_unused; reset_dependencies/reset_all give relations a hook to forget cached per-row state just before recompute.
**Invariant:** invalidation is monotone and terminating; a full-column invalidation must always pair with clearing that node's recorded dependencies (they will be rebuilt from actual accesses), and cycle detection is NOT this module's job (CircularRefError is thrown at evaluation from engine locks).
**Probe:** `sandbox/grist/test_depend.py::TestDependencies.test_recursive_column_dependencies` (:20–44, 3200-cell chain update without recursion failure) and `sandbox/grist/test_trigger_formulas.py::test_undo_should_restore_dependencies` (:704–731).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "depend Graph invalidate_deps add_edge relation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-map edge index + sentinel-collapsing worklist + relation-translated row propagation as the minimal lazy-dependency substrate. Adapt Node identity and Relation implementations to your storage model; omit the ninja-style order-only-deps idea (noted as future work upstream, unimplemented here). Live-test caveat: python-plane runner blocked this lane; probes pinned to test lines.
