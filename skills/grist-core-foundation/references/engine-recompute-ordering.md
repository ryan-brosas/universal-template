<!-- capsule-v2 -->
# Recompute ordering kernel — in what order does the engine evaluate dirty cells, and why is cross-column batching safe?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How does the data engine flatten nested dependencies onto an external work-item loop, reorder on out-of-order access, and detect cycles without building a topological sort?

## OrderError-driven WorkItem stack (engine.py)
**Path/Symbol:** `sandbox/grist/engine.py:Engine._update_loop` (:568–643), `_make_sorted_work_items` (:638–643), `_recompute` (:743–757), `_recompute_step` (:760–907), `prevent_recalc` (:1120–1125).
**Signature:** `_update_loop(work_items: list[WorkItem], ignore_other_changes=False)`; `_recompute_step(node, allow_evaluation=True, require_rows=None)`; `WorkItem = (node, row_ids|None, locks)`.
**Data Shape:** `self.recompute_map: dict[Node, SortedSet|ALL_ROWS]` drives everything; `_locked_cells` holds `(node,row_id)` pairs purely for cycle detection; `_recompute_done_map[node]` excludes finished rows within a round; `_changes_map[node]` collects `(row_id, previous, value)` triples for later calc/stored actions.

### Decisive source
```python
while work_items:
  node, row_ids, locks = work_items.pop()
  try:
    self._recompute_step(node, require_rows=row_ids)
  except OrderError as e:
    # Reorder: current item goes back (keeping its locks); the cell we followed is
    # scheduled FIRST with a lock so a true cycle surfaces as CircularRefError.
    work_items.append(WorkItem(node, row_ids, locks)); locks = []
    lock = (node, e.requiring_row_id)
    work_items.append(WorkItem(e.node, [e.row_id], [lock]))
    self._locked_cells.add(lock)
  for lock in locks:                       # discard locks only when item completes
    ...
    self._expected_done_counter += 1
    if self._recompute_done_counter < self._expected_done_counter:
      raise Exception('data engine not making progress updating dependencies')
if ignore_other_changes:
  break                                    # mlookup-only pass stops after explicit items
if self.recompute_map and self._recompute_done_counter == 0:
  raise Exception('data engine not making progress updating formulas')
work_items = self._make_sorted_work_items(self.recompute_map.keys())
# _make_sorted_work_items: sorted(nodes, reverse=True, key=lambda n: (not n.col_id.startswith('#lookup'), n))
```
Nested evaluation path (`_recompute`, :748–752): inside an update loop any needed recompute runs `_recompute_step(node, allow_evaluation=False)`, which raises `OrderError` instead of evaluating — that IS the flattening mechanism.

**Flow:** pop WorkItem -> `_recompute_step` evaluates REQUIRED rows first (itertools.chain of require_rows then dirty_rows), then opportunistically other dirty cells of the same column -> dependency access during evaluation triggers the nested allow_evaluation=False step which raises OrderError -> loop reorders (throwing cell scheduled before its dependent, locked) -> successful cells unlock themselves -> round ends; remaining nodes regenerate as sorted work items (#lookup columns first because metadata lookups must be fresh before ordinary formulas; reverse name order because the stack pops backwards) until recompute_map empties. Progress guards abort if a whole round computes nothing.
**Invariant:** formula evaluation NEVER nests across columns on the Python call stack; batching is safe because a cell evaluates at most once per round (exclude set + done counters), only strict-inequality changes are recorded (strict_equal gate in `_recompute_step` :888 before col.set), and prevent_recalc exemptions subtract rows into a NEW dirty set so the saved recompute_map entry survives for later evaluation.
**Probe:** `sandbox/grist/test_depend.py::TestDependencies.test_recursive_column_dependencies` (:20–44: updating row 1 of a 3200-row cumulative chain recomputes one cell at a time — the regression that forced the iterative unroll documented at depend.py :160–163).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "_update_loop OrderError work items recompute", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the external work-stack with exception-driven reordering and lock-based cycle detection whenever dependency graphs are discovered lazily during evaluation. Adapt the ordering heuristic (#lookup-first, name-descending) to host freshness needs; omit Grist mlookup special pass (ignore_other_changes) if you have no metadata lookups. Live-test caveat: python-plane runner blocked this lane; probe pinned to test lines.