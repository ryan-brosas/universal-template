<!-- capsule-v2 -->
# Geometry kernel — one Point/Matrix implementation, two runtimes, zero NaN leakage

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory `mnt-hdd-utopia-inspo-external-penpot` (re-pinned from stuck `ext-penpot` @dd6b521b — point.cljc/matrix.cljc/math.cljc byte-stable across the drift, spans verified). **Question:** How does penpot keep 2D geometry identical between JVM backend and JS frontend (serialization, equality, precision)?

## Connected graph-selected seam
**Path/Symbol:** `common/src/app/common/geom/point.cljc` : `point?`/`point`/arithmetic (:29-280) · `common/src/app/common/math.cljc` : `close?/almost-zero?/finite?` (:192-227) · `common/src/app/common/geom/matrix.cljc` : `Matrix` + `multiply!/multiply` + `inverse` (:24-416).
**Signature:** `(gpt/point x y) → #penpot/Point{:x :y}` · `(gmt/multiply m1 m2 & rest)` · `(gmt/inverse mtx)` · `(mth/close? a b [precision])`.
**Data Shape:** `Point` = defrecord(x y); `Matrix` = defrecord(^double a b c d e f) — SVG-order affine, printed as `matrix(a,b,c,d,e,f)` at precision 6.

### Decisive source
```clojure
;; matrix.cljc — nil IS the identity, mutation is host-split:
(defn multiply
  ([^Matrix m1 ^Matrix m2]
   (cond (and (nil? m1) (nil? m2)) (matrix)
         (nil? m1) m2                       ;; nil matrixes are equivalent to unit-matrix
         (nil? m2) m1
         :else (pos->Matrix (+ (* m1a m2a) (* m1c m2b)) …)))
  ([m1 m2 & others] (reduce multiply! (multiply m1 m2) others)))

#?@(:cljs [(set! (.-a m1) …) m1]           ;; multiply! mutates IN PLACE on JS only
    :clj   [(pos->Matrix …)])              ;; JVM returns a fresh record

;; math.cljc — every float comparison goes through one epsilon:
(def float-equal-precision 0.001)
(defn close? ([num1 num2] (close? num1 num2 float-equal-precision)) …)
(defn almost-zero? [num] (< (abs (double num)) 1e-4))

;; point.cljc — inverse of zero coords would produce Infinity; tests pin that:
(defn inverse [pt] (pos->Point (/ 1.0 (dm/get-prop pt :x)) (/ 1.0 (dm/get-prop pt :y))))
```

**Flow:** all geometry math routes through `app.common.math` reader-conditionals (`js/Math.*` vs `Math/*`) so CLJS gets raw doubles and CLJ gets boxed-safe calls → records carry Malli schemas with decode/encode hooks (`"x,y"` string ↔ point, `"matrix(...)"` ↔ Matrix) so persistence formats stay stable across runtimes → composition always via `multiply` (pure); hot loops use `multiply!` which mutates only on CLJS.
**Invariant:** never compare floats directly — `close?` (1e-3 for values, `almost-zero?` 1e-4 for zero tests) is THE equality; `inverse` returns nil on singular matrices (`almost-zero? det`) instead of throwing. Rotation is CLOCKWISE-positive in screen coords: `rotate-matrix` builds `[c s −s c]` with `-s` in slot c (grep pin: `grep -cF 'ns (- s)' common/src/app/common/geom/matrix.cljc` → 1); this convention is defined against the ROW-vector point application (`x' = x·a + y·c + e`) — flipping to column form silently transposes every rotation in the system.
**Probe:** `grep -cF 'pos->Point (/ 1.0 (dm/get-prop pt :x))' common/src/app/common/geom/point.cljc` → 1; direct test `matrix-str-roundtrip-test` (`grep -c 'matrix-str-roundtrip-test' common/test/common_tests/geom_test.cljc` → 1) pins str-form round-trip; `grep -c 'almost-zero?' common/src/app/common/geom/matrix.cljc` → 5 classification sites.
**Retrieve (live-resolved rank#1/#2: `multiply! … 155-184`, `multiply … 186-218`):**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"multiply nil unit matrix translate rotate scale","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the single-record/dual-runtime discipline + epsilon-equality funnel for any shared geometry model; adapt schema hooks to your serializer; omit OpenAPI type-properties if not exposing REST schemas. Tests: geom_point_test.cljc `add-points`…, geom_test.cljc matrix constructor/translate/scale/rotate deftests (:74-105), modifiers_test pins epsilon behavior end-to-end (runner blocked honestly).
