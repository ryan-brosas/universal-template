<!-- capsule-v2 -->
# Distribute space — how do you equalize gaps between shapes of different sizes without a second pass?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `penpot`. **Question:** How do you compute equal-spacing deltas for n arbitrarily-sized, possibly-rotated shapes in one forward loop?

## Sort-by-center + unit-space sequential repositioning
**Path/Symbol:** `common/src/app/common/geom/align.cljc:distribute-space` (:83-121).
**Signature:** `(distribute-space shapes axis)` → lazy seq of moved shapes (axis `:horizontal` | `:vertical`).
**Data Shape:** in: shape maps; out: same shapes after one `gsh/move` each. Axis selects coord (`:x`/`:y`) and size key (`:width`/`:height`) via two `if` splits.

### Decisive source
```clojure
space        (reduce - (size wrapper-rect) (map size wrapped-shapes))
unit-space   (/ space (- (count wrapped-shapes) 1))

deltas (loop [shapes' wrapped-shapes
              start-pos (coord wrapper-rect)
              deltas []]
  (let [first-shape (first shapes')
        delta       (- start-pos (coord first-shape))
        new-pos     (+ start-pos (size first-shape) unit-space)]
    (if (= (count shapes') 1)
      (conj deltas delta)
      (recur (rest shapes') new-pos (conj deltas delta)))))
```

**Flow:** union selection rect (`gsh/shapes->rect`) → sort shapes by CENTER coordinate on the axis → wrap each shape in its own rect (rotation-safe: wrapper of transformed points) → total free space = selection size − Σ item sizes → unit = space/(n−1) → forward loop assigns each shape `delta = slotStart − currentCoord`, then advances `slotStart += itemSize + unit`. Deltas are zipped back onto the *sorted* shapes and applied via `(gsh/move %1 (assoc (gpt/point) coord %2 other-coord 0))`.
**Invariant:** (1) First and last shapes participate: the first's delta is 0 by construction (wrapper starts at its coordinate) but is still computed — the last shape is pinned to the selection's far edge, so distribution is anchored at BOTH extremes. (2) What is equalized is the GAP between wrapping rectangles, not centers — centers of unequal shapes stay unequal by design (docstring: "what is distributed is the wrapping rectangles"). (3) n−1 division: an implicit single-shape call would divide by zero — callers gate with ≥3 selections upstream. (4) Sorting happens BEFORE wrapping; the delta seq must zip against the sorted order, not the input order.
**Probe:** `common/test/common_tests/geom_align_test.cljc` `valid-dist-axis-test` pins only the two-axis set (`= 2 (count gal/valid-dist-axis)`). No numeric distribute test exists at this pin — coverage caveat recorded; the arithmetic above is quoted from source :99-118 verbatim.
**Retrieve (live-resolved rank#1):**
```
search_graph {project:"penpot", query:"distribute-space unit-space wrapper", limit:5}
→ rank1 geom.align.distribute-space :83-121 (flex_layout layout_data.cljc distribute-space :164-174 is a DIFFERENT seam — auto-layout spacing, not manual distribution)
```

## Verdict
Adopt the center-sort + unit-interval + single-forward-loop algebra; it ports to any axis-keyed geometry. Adapt the group-cascade move semantics (`gsh/move` recurses into groups). Omit nothing else — beware the name twin in flex_layout when retrieving.
