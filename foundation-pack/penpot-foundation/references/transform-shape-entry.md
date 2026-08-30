<!-- capsule-v2 -->
# transform-shape entry — how do modifiers flow into geometry, and where do structure ops apply?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** What is the single entry contract that turns "modifiers attached to a shape" into a new shape, and what are its edge-case rules?

## Dissoc-modifiers, compile, apply; structure ops ride alongside
**Path/Symbol:** `common/src/app/common/geom/shapes/transforms.cljc` (`transform-shape` :483-500, `apply-objects-modifiers` :502-514, `transform-bounds` :516-524, `transform-selrect` :526-531, `transform-selrect-matrix` :533-538); root guard `cfh/root?`; emptiness `ctm/empty?`.
**Signature:** `(transform-shape shape)` → shape' (reads `:modifiers` off the shape and dissocs it) ; `(transform-shape shape modifiers)` → shape' ; `(apply-objects-modifiers objects modifiers ids)` → objects'.
**Data Shape:** shape may carry `:modifiers` inline (test fixtures do exactly this); root shape is exempt from geometric application; empty/nil modifiers short-circuit to the SAME shape.

### Decisive source
```clojure
(defn transform-shape
  ([shape]
   (let [modifiers (:modifiers shape)]
     (-> shape (dissoc :modifiers) (transform-shape modifiers))))
  ([shape modifiers]
   (if (and (some? shape) (some? modifiers) (not (ctm/empty? modifiers)))
     (let [transform (ctm/modifiers->transform modifiers)]
       (cond-> shape
         (and (some? transform)
              (not (cfh/root? shape)))
         (apply-transform transform)

         (ctm/has-structure? modifiers)
         (ctm/apply-structure-modifiers modifiers)))
     shape)))
```

**Flow:** entry normalizes by stripping `:modifiers` from the result payload (so applied shapes never leak op logs), compiles ops to ONE matrix via the ordered fold, applies it through the move/generic dispatch, then independently applies structure ops when present. Batch form iterates id-keyed modifier maps with `d/update-when`. The bounds/selrect helpers reuse the same pipeline for rectangles only (points→transform→AABB).
**Invariant:** (1) The `:modifiers` key MUST NOT survive into the returned shape — tests assert fixture equality on shapes without it; keeping it would re-apply on next pass (double-transform). (2) ROOT is geometry-immune but not structure-immune: `(not (cfh/root? shape))` gates ONLY `apply-transform` — a root board still receives add/remove-children/reflow/change-property. (3) Empty-modifier input returns the input UNCHANGED (identity by eq), which callers use as a "nothing to do" signal. (4) Structure application happens even when matrix compilation yields nil/unit — the two cond branches are independent.
**Probe:** direct tests `common/test/common_tests/geom_shapes_test.cljc` `transform-shapes` (:42-163): no-modifiers identity for rect AND path (:43-49); translation moves selrect x/y preserving w/h; EMPTY translation leaves all 8 rect props equal; resize doubles dims from fixed origin; **resize-to-zero yields selrect w=h=0.01** (:113-118: `grep -c 'close? 0.01' <file>` → 2 lines); rotation preserves point count + selrect x/y while moving points; rotation=0 no-op; invalid (Inf) selrect degrades gracefully via `close-rect?` (:153-163). Consumer test `change-dimensions-modifiers-end-to-end` (modifiers_test :166-179) exercises this exact entry through `gsh/transform-shape`.
**Retrieve (live-resolved rank#1/#2):**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"apply-transform dispatch move generic","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the strip-then-apply entry contract, the root exemption split, and the independent structure branch. Adapt the inline-vs-argument modifiers convention to your state plumbing (both arities are public API here). Omit nothing — this is the funnel every other capsule feeds.
