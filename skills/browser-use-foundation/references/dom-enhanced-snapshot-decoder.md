<!-- capsule-v2 -->
# CDP DOMSnapshot positional style decoding — how do you read computed styles from a flat snapshot without a renderer?

**Source:** browser-use MIT `main@85ddbfedf609166b2d2c76c3d80506649fee82a9`; Codebase Memory `mnt-hdd-utopia-inspo-agents-browser-use`. **Question:** how do CDP `DOMSnapshot.captureSnapshot` string tables decode into per-node styles, and where is the O(n²) trap?

## String-table + positional-index contract
**Path/Symbol:** `browser_use/dom/enhanced_snapshot.py:17-43` (`REQUIRED_COMPUTED_STYLES` :17, `_parse_computed_styles` :37); assembly in `build_snapshot_lookup` :46-181.
**Signature:** `_parse_computed_styles(strings: list[str], style_indices: list[int]) -> dict[str, str]`; `build_snapshot_lookup(snapshot, device_pixel_ratio=1.0) -> dict[int, EnhancedSnapshotNode]`.
**Data Shape:** CDP snapshot = `{strings: [..], documents: [{nodes: {backendNodeId[], isClickable: {index[]}}, layout: {nodeIndex[], bounds[], styles[][], paintOrders[], clientRects[], scrollRects[], stackingContexts}}]}`; output keyed by backendNodeId.

### Decisive source
```python
REQUIRED_COMPUTED_STYLES = ['display', 'visibility', 'opacity', 'overflow',
    'overflow-x', 'overflow-y', 'cursor', 'pointer-events', 'position',
    'background-color']  # order IS the protocol — positional, not keyed
def _parse_computed_styles(strings, style_indices):
    styles = {}
    for i, style_index in enumerate(style_indices):
        if i < len(REQUIRED_COMPUTED_STYLES) and 0 <= style_index < len(strings):
            styles[REQUIRED_COMPUTED_STYLES[i]] = strings[style_index]
    return styles
# bounds are DEVICE pixels:
bounding_box = DOMRect(x=raw_x / device_pixel_ratio, y=raw_y / device_pixel_ratio,
                       width=raw_width / device_pixel_ratio, height=raw_height / device_pixel_ratio)
```

**Flow:** build `backendNodeId → snapshot index` map → pre-build `layout nodeIndex → layout_idx` map keeping FIRST occurrence of duplicates (:79-85) → convert `isClickable.index` list to a set ONCE per document → for each node, look up its layout row and decode bounds (÷ devicePixelRatio), style indices (positional), paint orders, client/scroll rects, stacking contexts into an `EnhancedSnapshotNode`.
**Invariant:** the requested-style list passed to `captureSnapshot` and `REQUIRED_COMPUTED_STYLES` must stay index-aligned — the wire format carries no property names, so reordering either side silently swaps values. Bounds arrive in device pixels; dividing by DPR is mandatory or every coordinate is wrong on HiDPI. The list→set conversion of `isClickable.index` is load-bearing performance: membership on a 20k-element list was measured at 5,925ms total vs 2ms as a set (~3,000×) — the module's own comment names it "the #1 bottleneck". Duplicate `layout.nodeIndex` entries resolve to first occurrence.
**Probe:** no upstream unit test drives this module directly (coverage caveat) — downstream consumer `browser_use/dom/service.py` visibility/clickability detection and `dom/views.py::is_actually_scrollable` (see dom-views-scrollability-css-gate capsule) pin the decoded values' semantics.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-browser-use", query: "build_snapshot_lookup REQUIRED_COMPUTED_STYLES _parse_computed_styles", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the positional string-table decoder and the set-conversion perf pattern verbatim; adopt the 10-style minimal request list as a crash-avoidance default (comment: extra styles can crash Chrome on heavy sites). Adapt the style set to your consumers but NEVER reorder it independently of the capture call. Omit nothing.
