<!-- capsule-v2 -->
# Paint-order occlusion filter — disjoint rect unions decide which "visible" text is actually covered

**Source:** browser-use MIT `main@3c989dc0`; Codebase Memory `browser-use`. **Question:** Two elements both report is_visible=True, but a modal paints over one — how do you exclude the covered text from the LLM-facing DOM without a renderer?

## RectUnionPure: incoming-rect clipping with 5000-rect fail-open cap
**Path/Symbol:** `browser_use/dom/serializer/paint_order.py:RectUnionPure` (35-143), `Rect` (11-32), `PaintOrderRemover.calculate_paint_order` (165-225), `_document_context` (154).
**Signature:** `def add(self, r: Rect) -> bool`; `def contains(self, r: Rect) -> bool`; `_split_diff(a, b) -> list[Rect]` (≤4 pieces)
**Data Shape:** union = list of PAIRWISE-DISJOINT rects; keyed per `(session_id, frame_id)` context so iframe layers never occlude other documents.

### Decisive source
```python
# Safety cap: ... each add() can fragment existing rects into up to 4 pieces each.
# On heavy pages (20k+ elements) this can cause exponential growth. 5000 is generous...
_MAX_RECTS = 5000
def add(self, r):
    if len(self._rects) >= self._MAX_RECTS:
        return False                        # stop accepting; union stops growing
    if self.contains(r): return False       # already covered
    pending = [r]
    for s in self._rects:                   # clip INCOMING rect against existing members
        new_pending = []
        for piece in pending:
            if piece.intersects(s): new_pending.extend(self._split_diff(piece, s))
            else: new_pending.append(piece)
        pending = new_pending
    self._rects.extend(pending)             # leftover non-overlapping pieces join union
# calculate_paint_order: iterate paint order DESC so top-painted layers are in the union first
for paint_order, nodes in sorted(grouped_by_paint_order.items(), key=lambda x: -x[0]):
    if rect_unions[context].contains(rect): node.ignored_by_paint_order = True
    # skip transparent layers: bg rgba(0,0,0,0) or opacity < 0.8 ("highly vibes based number")
```

**Flow:** collect nodes having snapshot paint_order + bounds → group by paint_order → process groups from HIGHEST paint order down → per node: if its rect is fully contained in its document's union ⇒ mark `ignored_by_paint_order` (a later/lower layer painted UNDER something) → else add its rect to the union unless background fully transparent or opacity < 0.8 (translucent overlays must not hide content beneath).
**Invariant:** `add()` clips the INCOMING rect against existing members and never re-splits stored rects — the stored set stays pairwise-disjoint and grows ≤1 piece-count per op; `contains()` walks remaining pieces of the query across all union members. Cap semantics FAIL OPEN: past 5000 rects nothing more is added, `contains` under-covers, and filtering becomes conservative (fewer exclusions) — correctness (never hide real interactive content) beats aggressiveness. Per-document contexts prevent cross-iframe occlusion.
**Probe:** `tests/ci/test_dom_paint_order_serialization.py` (docstring pins the exact contract: "PaintOrderRemover.calculate_paint_order() correctly computes which nodes are fully covered... DOMTreeSerializer.serialize_tree() must respect that flag for TEXT_NODEs"). EXECUTED GREEN gate 5. Deterministic addendum executed green: duplicate add returns False; overlapping add keeps stored rects untouched; pairwise-disjoint invariant holds post-add; cap reached exactly at _MAX_RECTS.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "RectUnionPure calculate_paint_order ignored_by_paint_order", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt descending-paint-order + per-document disjoint rect unions + fail-open caps for any occlusion/visibility filter; adapt the opacity<0.8 threshold to your tolerance for false negatives; omit _split_diff only if you accept O(n·pieces) containment via rasterization elsewhere.
