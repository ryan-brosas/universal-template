<!-- capsule-v2 -->
# Cross-frame AX tree merge — visibility through iframe chains, disjoint index spaces

**Source:** browser-use MIT `<branch>@<commit>`; Codebase Memory `browser-use`. **Question:** how do you build one DOM view across main page + cross-origin iframes, decide real visibility through scrolled/clipped frames, and keep the LLM's index space separate from the executor's?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/dom/service.py` (1,231 lines): `_get_ax_tree_for_all_frames` (:357-400), `is_element_visible_according_to_all_parents` (:252+), `_count_hidden_elements_in_iframes` (:80), `_get_viewport_ratio` (:222); `dom/views.py`: `EnhancedDOMTreeNode` (:375-912, `compute_stable_hash` :830-858, xpath :492-516, scrollability :624-672), `SerializedDOMState` (:932-974) splitting `llm_representation` from `eval_representation`.
**Signature:** visibility = CSS gate × reverse ancestor-chain intersection (iframe offsets / document intersections with scroll) × optional viewport threshold (`None` = CSS-only).
**Data Shape:** per frame: full AX tree via CDP; merged node list rooted at main frame; geometry (bounds) shared across consumers.

### Decisive source
```ts
# merge: fan out Accessibility.getFullAXTree per frame, tolerate failures
results = await asyncio.gather(*[ax_tree(frame) for frame in all_frames], return_exceptions=True)
# detached/unreachable child frames -> debug log + skip, never fatal
# visibility:
if display:none or visibility:hidden or opacity<=0: return False   # CSS gate FIRST
bounds = copy(bounds)                    # snapshot bounds are SHARED — copy before mutating!
for frame in reversed(parent_html_frame_chain):
    if IFRAME/FRAME: offset bounds by frame position
    elif document:   bounds = intersect(bounds, frame.bounds - scroll)
    # a frame node appears in its own chain -> skip self
# two representations, one state:
SerializedDOMState(llm_representation=..., eval_representation=...)
```

**Flow:** collect every frame id → concurrent AX-tree fetches merged root-first → element visibility computed by walking its parent frame chain in reverse (offsets for iframes, intersection for documents, scroll accounted) so an element inside a scrolled-out iframe is invisible even when its own CSS says visible → internal `EnhancedDOMTreeNode` keeps stable hashes/xpaths while serialization produces TWO disjoint outputs: the indexed text the LLM reads and the lookup structure the executor resolves clicks against.
**Invariant:** detached frames degrade to skipped, not crashed; shared snapshot geometry is copied before any mutation; prompt indexes never collide with execution lookups (separate representations); tiny hidden iframes don't dominate hidden-element counts.
**Probe:** dom service call sites use retry-wrapped named tasks (`create_task_with_error_handling`) for ax_tree/viewport; structural test: llm vs eval representation builders are distinct.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_get_ax_tree_for_all_frames is_element_visible_according_to_all_parents SerializedDOMState llm_representation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt frame-tolerant AX merging, chain-aware visibility with copy-before-mutate geometry, and disjoint llm/eval representations. Adapt threshold semantics to host.
