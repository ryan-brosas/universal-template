<!-- capsule-v2 -->
# Lookup-map index lifecycle — how are invisible lookup index columns created, invalidated, and garbage-collected?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How does Grist give formulas fast lookups without real helper tables, and when do those index structures get freed?

## Index-as-formula-column + refcount GC
**Path/Symbol:** `sandbox/grist/lookup.py:LookupMapColumn` (:74-165), `SortedLookupMapColumn` (:169-224), `_RelationTracker/_delete_relation` (:361-412), `_LookupRelation` (:415-509), mappings (:228-357); engine side `sandbox/grist/engine.py:mark_lookupmap_for_cleanup` (:1281-1286), GC loop in `_bring_all_up_to_date` (:645-659), `#lookup`-first ordering (`_make_sorted_work_items` :638-643).
**Signature:** `LookupMapColumn(table, col_id, col_ids_tuple)`; `do_lookup(self, key) -> (row_ids, Relation)`.
**Data Shape:** helper col ids like `#lookup#Email` / `#lookup#Email#Date` (never visible columns); mapping = TwoWayMap rowId ↔ key tuples (`SimpleLookupMapping` one key per row vs `ContainsLookupMapping` product-of-groups for CONTAINS lookups); per-key `LookupSet` caches `.sorted_versions[sort_spec] -> sorted row_ids`.

### Decisive source
```python
# lookup.py :89-102 — an index that IS a formula column
  def __init__(self, table, col_id, col_ids_tuple):
    # Note that self._recalc_rec_method is passed in as the formula's "method".
    col_info = column.ColInfo(usertypes.Any(), is_formula=True, method=self._recalc_rec_method)
    super(LookupMapColumn, self).__init__(table, col_id, col_info)
...
    engine.invalidate_column(self)
    self._relation_tracker = _RelationTracker(engine, self)
```
```python
# engine.py :653-658 — GC only after everything settles
      # Check if any potentially unused LookupMaps are still unused, and if so, delete them.
      for lookup_map in self._unused_lookups:
        if self.dep_graph.remove_node_if_unused(lookup_map.node):
          self.delete_column(lookup_map)
    finally:
      self._unused_lookups.clear()
# lookup.py :409-412
  def _delete_relation(self, referring_node):
    self._lookup_relations.pop(referring_node, None)
    if not self._lookup_relations:
      self._engine.mark_lookupmap_for_cleanup(self._lookup_map)
```

**Flow:** first `lookupRecords(...)` creates a LookupMapColumn (+ optional Sorted twin): it registers as a FORMULA column whose "formula" (`_recalc_rec_method`) updates the row↔key map in O(1) and invalidates referring rows via tracked relations — so ordinary dirty-set recomputation maintains the index. A caller's `do_lookup` records a `_LookupRelation` entry (referring row ↔ keys looked up) and creates a dependency via `engine._use_node`; sort changes only clear cached `.sorted_versions` entries (`_reset_sorted_versions`). `_invalidated_keys_cache` dedups repeated key invalidations to prevent O(N²) blowups and resets whenever relations rebuild (:435-438, :504-509). When the LAST relation for a map deletes, the tracker marks the map for cleanup; after the update loop finishes, still-unused maps pass `dep_graph.remove_node_if_unused(node)` and get deleted. The `#lookup`-first work-item ordering exists precisely because lookup nodes don't know their dependents until recomputed (see comment :639-641).
**Invariant:** An index column must be deleted only when BOTH unused by relations AND its dep node is removable; invalidations routed through relations must be idempotent within a round.
**Probe:** direct tests exercise this end-to-end rather than by internal name — `test_lookup_sort.py`/`test_lookups.py` pin lookup+sort behavior through engine runs. COVERAGE CAVEAT: no test references `mark_lookupmap_for_cleanup` explicitly; GC path pinned deterministically to engine.py :653-658 and lookup.py :409-412 (line-verified this run).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", mode: "ids", query: "LookupMapColumn mark_lookupmap_for_cleanup remove_node_if_unused", limit: 10 });
```

## Verdict
Adopt "index as hidden formula column" so existing recalc machinery maintains it, plus mark-then-sweep-after-quiescence GC. Adapt relation bookkeeping granularity to your cell graph. Omit CONTAINS product-mapping unless list-typed lookup keys exist.
