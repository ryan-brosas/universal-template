<!-- capsule-v2 -->
# Modifiers application — how does an op log become one matrix, and how do structure ops mutate the tree?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory `mnt-hdd-utopia-inspo-external-penpot` (re-pinned from stuck `ext-penpot` @dd6b521b — modifiers.cljc byte-stable across the drift, spans verified :591-652/:712-757). **Question:** How are accumulated modifiers folded into a single affine matrix (and applied to shape data), including the resize-with-pre-transform case that a naive port gets wrong?

## Connected graph-selected seam
**Path/Symbol:** `common/src/app/common/types/modifiers.cljc` : `transform-move!` (:591-596) / `transform-resize!` (:599-619) / `transform-rotate!` (:621-631) / dispatch `transform!` (:633-640) / `modifiers->transform` (:646-652) + `apply-modifier`/`apply-structure-modifiers` (:712-757).
**Signature:** `(modifiers->transform modifiers)` → Matrix · `(apply-modifier shape operation)` → shape' · `(apply-structure-modifiers shape modifiers)` → shape''.
**Data Shape:** geometry ops fold left-to-right into a 2D-affine `Matrix` (a b c d e f); structure ops (`:add-children`, `:remove-children`, `:scale-content`, `:change-property`, `:rotation`) edit the shape map itself.

### Decisive source
```clojure
(defn- transform-resize!
  [matrix modifier]
  (let [tf     (dm/get-prop modifier :transform)
        tfi    (dm/get-prop modifier :transform-inverse)
        vector (dm/get-prop modifier :vector)
        origin (dm/get-prop modifier :origin)
        origin (if ^boolean (some? tfi)
                 (gpt/transform origin tfi)   ;; origin mapped INTO LOCAL space first
                 origin)]
    (gmt/multiply!
     (-> (gmt/matrix)
         (cond-> ^boolean (some? tf)   (gmt/multiply! tf))
         (gmt/translate! origin)
         (gmt/scale! vector)
         (gmt/translate! (gpt/negate origin))
         (cond-> ^boolean (some? tfi)  (gmt/multiply! tfi)))
     matrix)))

(defn modifiers->transform
  [modifiers]
  (let [modifiers (concat (dm/get-prop modifiers :geometry-parent)
                          (dm/get-prop modifiers :geometry-child))
        modifiers (sort-by #(dm/get-prop % :order) modifiers)]
    (modifiers->transform1 modifiers)))
```

**Flow:** flatten `geometry-parent ++ geometry-child` → sort by `:order` → reduce `transform!` dispatching on `:type` (move = premultiplied translation; resize = the five-matrix sandwich `tf·T(origin)·S(v)·T(−origin)·tf⁻¹`; rotation = T(center)·R(angle)·T(−center)). Every builder multiplies ONTO THE LEFT of the accumulator, matching the row-vector point application (`x' = x·a + y·c + e`) — chronological order survives because `:order` is globally assigned at build time and buckets never change application sequence, only propagation scope. Structure side: `apply-modifier` is a `case` over op type — `:rotation` wraps angle with `(mod (+ rot Δ) 360)`, `:add-children` inserts at index then DEDUPES via `ordered-set`, `:remove-children` filters via set membership, unknown types return the shape UNCHANGED (default arm :749-750).
**Invariant:** (1) resize of a transformed shape must be expressed in the shape's LOCAL frame — origin is pre-mapped through `transform-inverse` AND the whole scale sandwiched between `tf…tfi`; skipping EITHER half applies screen-space scaling to local geometry and shears rotated shapes (grep pin: `grep -cF '(gpt/transform origin tfi)' common/src/app/common/types/modifiers.cljc` → 1). (2) The final matrix is order-sensitive; never sort by anything but `:order` (grep pin: `grep -cF 'sort-by #(dm/get-prop % :order)' <same>` → 1). (3) Structure application is INDEPENDENT of geometry compilation — an empty/unit matrix still lets structure ops through.
**Probe:** direct tests in `common/test/common_tests/types/modifiers_test.cljc`: `modifiers->transform` (:20-32, six mixed ops produce non-identity); `change-dimensions-modifiers-end-to-end` (:166-179, real selrect after `gsh/transform-shape`); `apply-modifier-test` (:574-632, incl rotation mod-360 wrap :583-589 and unknown-op no-op :629-632). Source census: `grep -c 'merge-child?' types/modifiers.cljc` → 2 gates guard cross-bucket merging in `add-modifiers` (:398-399).
**Retrieve (live-resolved rank#1: `transform-resize! Function … 599-619`):**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"modifiers->transform sort order resize origin transform-inverse","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the matrix-funnel (one sorted op list → one matrix) plus local-frame resize sandwich with pre-transformed origin; adapt structure ops to your schema; omit WASM mirror semantics (render-wasm has its own propagate_modifiers in Rust — out of scope here). Test anchors executed: `modifiers->transform`, `apply-modifier-test`, `change-size-basic` in modifiers_test.cljc (31 deftests, runner blocked honestly — JVM deps absent in inspo clone).
