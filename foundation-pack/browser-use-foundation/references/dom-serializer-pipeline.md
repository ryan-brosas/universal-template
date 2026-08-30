<!-- capsule-v2 -->
# DOM serialization pipeline — AX tree to LLM-safe simplified tree with stable indices

**Source:** browser-use MIT `<branch>@<commit>`; Codebase Memory `browser-use`. **Question:** how does a 100k-node DOM become a compact interactive-element list the LLM can act on, with indices that survive across steps?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/dom/serializer/serializer.py` (1,332 lines): `DOMTreeSerializer` (:41) — `serialize_accessible_elements` (:110-161), `_create_simplified_tree` (:451+), `_optimize_tree` (:558), `_assign_interactive_indices_and_mark_new_nodes`, `_add_compound_components` (:163), `_extract_select_options` (:348); support: `paint_order.py` (`PaintOrderRemover`), `clickable_elements.py`; source tree from `dom/service.py` (`DomService` :45, CDP AX tree for all frames incl. cross-origin iframes :357).
**Signature:** serialization = fixed 5-phase pipeline returning `(SerializedDOMState{_root, selector_map}, timing_info)`; every phase is timed.
**Data Shape:** `EnhancedDOMTreeNode` (raw, with shadow roots + content documents) → `SimplifiedNode` (pruned) → selector map `{index -> backend_node_id}`; per-element skip lists: DISABLED_ELEMENTS, SVG_ELEMENTS, `data-browser-use-exclude` attrs (session-scoped variant supported).

### Decisive source
```ts
# Phase order (each timed):
simplified_tree = self._create_simplified_tree(self.root_node)   # 1 prune
PaintOrderRemover(simplified_tree).calculate_paint_order()       # 2 drop occluded
optimized_tree   = self._optimize_tree(simplified_tree)          # 3 collapse parents
filtered_tree    = self._apply_bounding_box_filtering(...)       # 3.5 viewport cut
self._reserve_backend_node_ids(filtered_tree)                    # 4 stable ids
self._assign_interactive_indices_and_mark_new_nodes(filtered_tree)
# pruning rules inside _create_simplified_tree:
#   - ALWAYS keep shadow-DOM fragments ('actual interactive content in SPAs')
#   - IFRAME/FRAME -> recurse into content_document (cross-origin handled upstream)
#   - aria-*/pseudo attrs force visibility=True (validation elements)
```

**Flow:** CDP accessibility tree fetched across ALL frames → simplified tree prunes junk but keeps shadow hosts and iframe interiors → paint-order removal drops visually occluded elements → parent collapsing shrinks depth → bbox filter cuts offscreen → indices assigned in deterministic order and mapped to backend node ids so the actor can click by index later.
**Invariant:** index assignment happens LAST (after all pruning) so numbers are dense and stable; occluded/offscreen elements removed before indexing; shadow DOM never dropped; every element the LLM sees resolves to a real clickable node via the selector map.
**Probe:** `tests/` dom tests (shadow content retained; occluded removed by paint order; index stability across serializations; select options extracted).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "serialize_accessible_elements simplified tree paint order interactive indices selector_map", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the phased DOM→LLM serializer (prune → paint-order → collapse → bbox → index-last) with a selector-map bridge back to real nodes; adapt skip lists to host.
