<!-- capsule-v2 -->
# Snap-point vocabulary — which points exist, when do guides go silent, and what gates grid snapping?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `penpot`. **Question:** What is the complete candidate set a snap engine offers per shape kind, and under which context guards do candidates disappear?

## Corner+center sets, frame midpoint enrichment, guide suppression, display-gated grid lines
**Path/Symbol:** `common/src/app/common/geom/snap.cljc` (`rect->snap-points` :16-27, `frame->snap-points` :29-41, `shape->snap-points` :43-48, `guide->snap-points` :50-62); `common/src/app/common/geom/grid.cljc:grid-snap-points` (:111-134).
**Signature:** `(rect->snap-points rect)` → set|nil ; `(shape->snap-points shape)` → set ; `(guide->snap-points guide frame)` → set (possibly empty) ; `(grid-snap-points shape grid coord)` → seq-of-points|nil.
**Data Shape:** snap sets are Clojure sets of `gpt/point` records — set semantics dedup coincident corners; guides are `{:axis :x|:y :position n}`; grids are the same maps as `grid-generic-algebra` plus `:display`.

### Decisive source
```clojure
(defn guide->snap-points
  [guide frame]
  (cond
    (and (some? frame)
         (not ^boolean (ctst/rotated-frame? frame))
         (not ^boolean (cfh/is-direct-child-of-root? frame)))
    #{}                                    ;; silent inside plain nested frames

    (= :x (:axis guide))
    #{(gpt/point (:position guide) 0)}

    :else
    #{(gpt/point 0 (:position guide))}))

;; grid.cljc
(when (:display grid)                      ;; invisible grid ⇒ NO snap points at all
  (case type
    :square (when (> size 0) ... interior step lines per axis ...)
    :column (when (= coord :x) (->> (grid-areas shape grid) (mapcat grid-area-points)))
    :row    (when (= coord :y) ...))))
```

**Flow:** rects contribute exactly 4 corners + center; FRAMES add 4 edge midpoints (8 total — computed from `points->rect`, so rotation-safe); non-frame shapes contribute their raw corner `:points` ∪ center. Guides normally emit one axis-aligned point at their position, but return the EMPTY set when snapped inside a frame that is neither rotated nor a direct child of root. Grid candidates exist only when `:display` is true, are axis-filtered (column→`:x` only, row→`:y` only), and square-grid size must be > 0.
**Invariant:** (1) Sets, not lists — duplicated corner coordinates collapse silently, so "5 points" for a rect is an emergent property of point-record equality (test-pinned count). (2) Guide suppression is tri-conditional with the rotated-frame ESCAPE HATCH last — reorder the conditions and root-level alignment breaks. (3) Grid nil vs empty matters: `nil` means "no grid contribution" (test asserts `nil?`), distinct from an empty seq. (4) Frame midpoints come from the rect derived FROM `:points`, never from stale selrect fields.
**Probe:** `common/test/common_tests/geom_snap_test.cljc`: `rect->snap-points-test` (count = 5; center present exactly once; nil rect → nil), `shape->snap-points-test` (≥5 from points∪center), `guide->snap-points-test` (x-guide → `{(100,0)}`, y-guide → `{(0,200)}`); `geom_grid_test.cljc` `grid-snap-points-test` (`display false` → nil; column on `:y` → nil). Runner block: no clojure CLI available.
**Retrieve (live-resolved rank#1–#3/#5):**
```
search_graph {project:"penpot", query:"snap-points frame guide rect corners center", limit:5}
→ rank1 geom.snap.rect->snap-points :16-27 · #2 geom.snap.guide->snap-points :50-62 · #3 geom.snap.frame->snap-points :29-41 · #5 frontend main.snap.get-snap-points :83-94 (consumer)
```

## Verdict
Adopt the vocabulary tiers (rect ⊂ frame) and the set-based dedup; adopt the guide-suppression guard order verbatim if you port alignment guides. Adapt point-record equality to your geometry type (value equality is load-bearing). Omit the frontend consumer's proximity ranking — that lives outside this plane.
