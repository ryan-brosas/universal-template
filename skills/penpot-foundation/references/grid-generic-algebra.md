<!-- capsule-v2 -->
# Grid geometry algebra — one generic calculator, three grid kinds, every parameter optionally derived

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `penpot`. **Question:** How do column/row/square grids share one computation, and how do size/item-length/gutter/offset mutually derive without circularity?

## `[size item-length next-v gutter]` tuple + type-keyed offset/stretch
**Path/Symbol:** `common/src/app/common/geom/grid.cljc` (`calculate-default-item-length` :15-18, `calculate-size` :20-25, `calculate-generic-grid` :27-52, `calculate-column-grid` :54-57, `calculate-row-grid` :59-62, `calculate-square-grid` :64-74, `grid-gutter` :76-88, `grid-areas` :90-102).
**Signature:** `(grid-areas frame grid)` → seq of `{:x :y :width :height}` ; private `(calculate-generic-grid v total-length params)` → `[size item-length next-v gutter]`.
**Data Shape:** frame = plain rect map; grid = `{:type :column|:row|:square :params {:size :item-length :gutter :margin :type}}`; params `:type` ∈ default(margin) | `:center` | `:right` | `:stretch`.

### Decisive source
```clojure
(defn- calculate-generic-grid
  [v total-length {:keys [size gutter margin item-length type]}]
  (let [size   (if (number? size)  size
                 (calculate-size total-length item-length margin gutter))
        parts  (/ total-length size)
        item-length (if (number? item-length) item-length
                      (+ parts (- gutter) (/ gutter size) (- (/ (* margin 2) size))))
        offset (case type
                 :right  (- total-length (* item-length size) (* gutter (dec size)) margin)
                 :center (/ (- total-length (* item-length size) (* gutter (dec size))) 2)
                 margin)
        gutter (if (= :stretch type)
                 (let [gutter (max 0 gutter (/ (- total-length (* item-length size) (* margin 2)) (dec size)))]
                   (if (d/num? gutter) gutter 0))
                 gutter)
        next-v (fn [cur-val] (+ offset v (* (+ item-length gutter) cur-val)))]
    [size item-length next-v gutter]))
```

**Flow:** resolve `size` first (given OR floor-derived from item-length: `floor(len−(m+(−m+g)))/ (item+gutter)`), then derive missing `item-length` from parts — the two derivations are ordered so only ONE may be absent → compute per-type offset (default = margin; `:center`/`:right` distribute leftover width; `:right` also re-subtracts margin) → `:stretch` recomputes gutter as `max(0, given, remainder/(n−1))` with a NaN-poison `d/num?` guard falling back to 0 → return a position CLOSURE `next-v` so `grid-areas` can just `(map next-x (range num-items))`. Column binds the tuple to x-axis and pins y constant; row mirrors; square is a separate quot-based tiler whose next-x/next-y decode `(quot idx col-size)/(rem idx col-size)`.
**Invariant:** (1) Exactly one of size/item-length may be derived; both given wins for size. (2) `next-v` closes over offset+step — area positions are pure functions of the flat index. (3) The `:stretch` max() starts at literal 0, so negative computed gutters cannot escape; non-number results become 0, not errors. (4) Square-grid count is `(* col-size row-size)` with `col-size = (quot width cellSize)` — truncating division, no partial tiles.
**Probe:** `common/test/common_tests/geom_grid_test.cljc`: `calculate-default-item-length-test` (1200/64/16 → exactly 896/12; zeros → 100.0), `calculate-size-test` (1000/100/0/10 → 9 with floor), `grid-areas-column-test` (3 areas), `grid-areas-square-test` (all areas exactly 50×50). Runner block: no clojure CLI available — tests read directly.
**Retrieve (live-resolved rank#1/#2/#4):**
```
search_graph {project:"penpot", query:"grid-areas column row square gutter margin", limit:5}
→ rank1 geom.grid.grid-gutter :76-88 · #2 geom.grid.grid-areas :90-102 · #4 geom.grid.calculate-square-grid :64-74 (icon.cljs name-twins are noise)
```

## Verdict
Adopt the tuple-plus-closure shape and the derivation ordering; adopt the stretch-gutter max(0,…)+num? ladder verbatim. Adapt the case on `:type` to your layout vocabulary. Omit the frontend icon name-collisions when retrieving — filter to `geom.grid`.
