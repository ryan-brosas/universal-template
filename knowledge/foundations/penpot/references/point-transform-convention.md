<!-- capsule-v2 -->
# Point & center primitives — which transform convention does the whole geometry stack assume?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** Is a point transformed as row or column vector — and how are centers derived so every rotate/scale-about-center helper stays consistent?

## Row-vector application + AABB midpoint centers
**Path/Symbol:** `common/src/app/common/geom/point.cljc` (`transform` :330-345, `transform!` :348-370, `to-vec` :381-382, `dot` :389-394, `add` :125-, `negate` :203-, `divide` :165-); `common/src/app/common/geom/shapes/common.cljc` (`points->center` :30-39 with keep-xforms :17-18, `shape->center` :41-44, `transform-points` :46-59, `transform-selrect` :61-77).
**Signature:** `(gpt/transform p m)` → point' ; `(transform-points points center matrix)` → [points] ; `(points->center points)` → point.
**Data Shape:** Point = `#penpot/point {:x :y}` record; matrix fields a-f; optional `center` argument wraps any transform into about-center form.

### Decisive source
```clojure
(defn transform
  "Transform a point applying a matrix transformation."
  [p m]
  (when (point? p)
    (if (some? m)
      (let [x (:x p) y (:y p) a (:a m) b (:b m) c (:c m) d (:d m) e (:e m) f (:f m)]
        (pos->Point (+ (* x a) (* y c) e)
                    (+ (* x b) (* y d) f)))
      p)))

;; points->center = ((min+max)/2 per axis) via transducer keep of x then y
```

**Flow:** every matrix application in the stack funnels through this row-vector form (`x' = x·a + y·c + e`, NOT the column-form `a·x + c·y + e`) — this is why `multiply!` composes matrices the way it does and why premultiplied modifier chains apply in chronological order. `transform-points` optionally brackets the matrix with translate(+center)/translate(−center) built from CLONED unit base. Centers come exclusively from AABB midpoints of corner points (`points->center`) or selrect rect-center (`shape->center`) — never centroid-of-area.
**Invariant:** (1) Flipping to column-vector convention silently TRANSPOSES every rotation in the system; the clockwise-positive screen rotation in `rotate-matrix` is defined against THIS convention. (2) Center = AABB midpoint means rotating a shape does NOT move its center (corners rotate around it) but resizing along one edge DOES; porters substituting true centroids break flip detection (dot products use p0-anchored edges from these same corners). (3) nil-matrix tolerance: `transform` returns p unchanged when m is nil — mirrors multiply's nil-as-unit.
**Probe:** direct tests `common/test/common_tests/geom_test.cljc` (point constructors/add/subtract/distance/length/angle deftests :15-72) and `common/test/common_tests/geom_point_test.cljc` (321L); consumer pins: `grep -c 'translate-matrix-neg center' common/src/app/common/geom/shapes/common.cljc` → 1 (the about-center bracket inside transform-points).
**Retrieve (live-resolved rank#1/#2):**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"transform-points-matrix recover matrix from corners","limit":5,"detail":"ids"}'
```
(same plane; for point-level queries route by Source line — `gpt/dot` resolves rank 2 on the adjust-shape-flips query.)

## Verdict
Adopt row-vector application and AABB-midpoint centers as THE convention. Adapt the record/transducer plumbing. Omit `matrix->point` translation-only accessor trivia.
