<!-- capsule-v2 -->
# Move-vs-generic transform dispatch — why does a pure translation take a different code path than any other transform?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** When applying a matrix to a shape, when must you rewrite x/y/width/height in place versus regenerate selrect+transform — and how is that decision made?

## The three-arm dispatch keyed on the move predicate
**Path/Symbol:** `common/src/app/common/geom/shapes/transforms.cljc` (`apply-transform` :376-388, `apply-transform-move` :315-335, `apply-transform-generic` :338-374; predicate `gmt/move?` at `common/src/app/common/geom/matrix.cljc`:410-415).
**Signature:** `(apply-transform shape transform-mtx)` → shape' ; `(move? m)` → boolean.
**Data Shape:** shape carries `:points` (4 corners), `:selrect`, optional `:x :y :width :height`, `:type` (`:text` / `:path` / `:bool` special), `:position-data` (text only), `:content` (path/bool only); matrix may be nil (= no-op, returns shape unchanged).

### Decisive source
```clojure
(defn apply-transform
  [shape transform-mtx]
  (cond
    (nil? transform-mtx)
    shape

    ^boolean (gmt/move? transform-mtx)
    (apply-transform-move shape transform-mtx)

    :else
    (apply-transform-generic shape transform-mtx)))
;; move? = a≈1 b≈0 c≈0 d≈1  (translation-only detection via almost-zero?, 1e-4)
```

**Flow:** nil → identity. Pure translation (`move?`) → `apply-transform-move`: points and selrect translated, text gets `:position-data` shifted, path/bool content translated, plain shapes get x/y/w/h ASSOC'd from the moved selrect — NO transform regeneration, flip flags untouched. Any other affine (resize/rotation/skew/flip) → `apply-transform-generic`: flips re-derived from corner vectors FIRST (`adjust-shape-flips`), then center/selrect recomputed from transformed points, NEW transform+inverse recovered (`calculate-transform`; on degenerate geometry falls back to the shape's EXISTING `:transform`/`:transform-inverse` or unit matrices :350-355), rotation re-normalized `mod(...,360)`.
**Invariant:** (1) The dispatch predicate is `move?` on the MATRIX, not on modifier types — an accumulated modifiers chain that happens to collapse to pure translation still takes the cheap path. (2) The generic arm MUST run `adjust-shape-flips` before storing anything: it toggles flip-x/flip-y by the SIGN of dot products of old-vs-new edge vectors (:285-313) and negates `:rotation` ONLY when exactly one axis flipped — flipping both axes equals 180° rotation and two negations cancel (comment :309-311). (3) Path/bool shapes never store x/y/w/h updates from the generic arm's assoc branch — their `:content` absorbs the transform instead (:362-363); porting the assoc unconditionally corrupts path geometry with an AABB. (4) Text `:position-data` moves under BOTH arms but only via its dedicated updater.
**Probe:** `common/test/common_tests/geom_shapes_test.cljc` — dispatch census: `grep -cF '(gmt/move? transform-mtx)' common/src/app/common/geom/shapes/transforms.cljc` → 1; flip behavior pinned by `flip-x-only-toggles-flip-x-and-negates-rotation` (:236-250: rotation 30→330 after scale(-1,1)), `flip-y-only...` (:252-261: 45→315), `flip-both-axes-toggles-both-flags-but-preserves-rotation` (:263-273: 30 stays 30) — `grep -c 'flip-x-only-toggles\|flip-y-only-toggles\|flip-both-axes-toggles' <test file>` → 3.
**Retrieve (live-resolved rank#1/#2):**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"apply-transform dispatch move generic","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the matrix-keyed dispatch and the flip/rotation sign algebra (dot-product rule + single-axis negation). Adapt which shape types get inline x/y/w/h vs content-absorbed treatment to your schema. Omit the FIXME performance notes' implied refactor (source itself defers it).
