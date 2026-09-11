<!-- capsule-v2 -->
# Affine recovery from corners — how do you get back the transform matrix from only the four corner points?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** Given a shape's selrect and its four transformed corner points, how do you reconstruct the 2×3 affine matrix that produced them — and what does a porter get catastrophically wrong here?

## The closed-form corner→matrix solve with a structurally-dead term
**Path/Symbol:** `common/src/app/common/geom/shapes/transforms.cljc` (`transform-points-matrix` :188-236, `calculate-selrect` :238-257, `calculate-transform` :259-276, `calculate-geometry` :278-283).
**Signature:** `(transform-points-matrix selrect [d1 d2 _ d4])` → Matrix-or-nil ; `(calculate-selrect points center)` → Rect ; `(calculate-transform points center selrect)` → Matrix-or-nil ; `(calculate-geometry points)` → `[selrect transform inverse]`.
**Data Shape:** input points are the rect's corners in order p0=TL, p1=TR, p2=BR, **p3=BL** (p3 unused by the solve; destructured as `_`); selrect is the UNtransformed axis-aligned rect; matrix coefficients are individually passed through `mth/round-to-zero`.

### Decisive source
```clojure
(defn transform-points-matrix
  [selrect [d1 d2 _ d4]]
  ;; If the coordinates are very close to zero (but not zero) the rounding can mess with the
  ;; transforms. So we round to zero the values
  (let [x1  (mth/round-to-zero (dm/get-prop selrect :x1))
        ...
        det (+ (- (* (- y1 y2) x1)
                  (* (- y1 y2) x2))
               (* (- y1 y1) x1))]
    (when-not (zero? det)
      ... mb0 (/ (- y1 y2) det)
          mb4 (/ (- x1 x1) det)     ;; ≡ (/ 0 det) = 0 ALWAYS
      ...)))
```

**Flow:** `calculate-geometry` derives center from points min/max, rebuilds width/height via `mth/hypot` of corner distances (so width survives rotation), solves the matrix from corner correspondences, and returns `[selrect transform inverse]`. `calculate-transform` then recentres: `translate-matrix-neg(center) · M · translate(center)`, and returns the shared unit constant `gmt/base` if the result is numerically unit.
**Invariant:** (1) THE DEAD TERMS: `mb4 = (- x1 x1)` is identically zero, so the b-coefficient column terms `ma0·mb4 + ma1·mb7 + ma2·mb8` (:225) and `ma3·mb4 + ma4·mb4 + ma5·mb8` (:234) receive NO contribution from ma0/ma3 — this is not an optimization to "fix"; it is load-bearing structure of the closed-form solve. A naive reimplementation with a symmetric 3×3 inverse will NOT reproduce these formulas. (2) `det` collapses to `(- (* (- y1 y2) x1) (* (- y1 y2) x2))` because the `(- y1 y1)` term is identically 0 — degenerate rects (zero height or zero width after rounding) return nil and callers must keep prior geometry. (3) Every coefficient AND every selrect coordinate passes `round-to-zero` (10 sites :192-207) BEFORE arithmetic; skipping this turns near-zero floats into garbage transforms. (4) The unit-matrix guard returns the SHARED `gmt/base` constant, preserving identity comparison downstream.
**Probe:** `common/test/common_tests/geom_shapes_test.cljc` `points-transform-matrix` (:180-222) — table-driven: no-op→identity; displacement→`(matrix 1 0 0 1 20 20)`; resize→`(2 0 0 4 0 0)`; displacement+resize→`(2 0 0 4 10 10)`; rotation 45°→cos/sin form; rotation+resize→column-scaled cos/sin. Direct-test count: `grep -c 'points-transform-matrix' common/test/common_tests/geom_shapes_test.cljc` → 1. Source census pins: `grep -c 'round-to-zero' common/src/app/common/geom/shapes/transforms.cljc` → 10 ; `grep -c 'mb4' <same file>` → 3 (:213 definition + uses :226/:229).
**Retrieve (live-resolved rank#1):**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"transform-points-matrix recover matrix from corners","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the corner-correspondence recovery approach, the round-to-zero discipline, the det-nil degenerate contract, and the unit→shared-base normalization. Adapt the specific coefficient layout only WITH its dead terms intact (do not re-derive). Omit the wasm twin `render-wasm/src/math.rs Bounds::transform_matrix` (forward application, different problem).
