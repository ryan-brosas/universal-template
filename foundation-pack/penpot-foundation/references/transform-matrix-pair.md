<!-- capsule-v2 -->
# transform-matrix / inverse-transform-matrix pair — how is a shape's stored rotation+flip rendered as one SVG matrix?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** How do the scalar fields (`:rotation`, `:flip-x`, `:flip-y`, optional `:transform`) compose into a single render-time matrix, and what is its exact inverse relationship?

## About-center sandwich with no-flip escape hatch
**Path/Symbol:** `common/src/app/common/geom/shapes/transforms.cljc` (`transform-matrix` :121-143, `inverse-transform-matrix` :145-165, `transform-str` :167-177).
**Signature:** `(transform-matrix shape)` / `(transform-matrix shape params)` / `(transform-matrix shape params center)` → Matrix ; `(transform-str shape params)` → string.
**Data Shape:** reads `:flip-x :flip-y :transform :transform-inverse`; `params {:keys [no-flip]}` suppresses flip composition (used by exporters that bake flips elsewhere); center defaults to `shape->center` else (0,0).

### Decisive source
```clojure
([{:keys [flip-x flip-y transform] :as shape} {:keys [no-flip]} shape-center]
 (-> (gmt/matrix)
     (gmt/translate shape-center)
     (cond-> (some? transform)  (gmt/multiply transform))
     (cond-> (and flip-x no-flip) (gmt/scale (gpt/point -1 1)))
     (cond-> (and flip-y no-flip) (gmt/scale (gpt/point 1 -1)))
     (gmt/translate (gpt/negate shape-center))))

;; inverse pair: flips FIRST, then transform-inverse
```

**Flow:** forward = translate(center)·transform·flipX?·flipY?·translate(−center); inverse = translate(center)·flipX?·flipY?·transform-inverse·translate(−center). The ORDER DIFFERENCE between the two bodies IS the inversion — porters who mirror the same body and swap only `transform→transform-inverse` produce wrong matrices when both flips AND transforms exist. `transform-str` emits the SVG `matrix(...)` attribute string at 6-decimal precision, returning "" when there is nothing to express.
**Invariant:** (1) Flips are ±1 SCALE matrices about the center, never point negation. (2) `no-flip` gates BOTH flips symmetrically and exists because some consumers apply flips at a different layer — dropping it double-flips. (3) The pair's correctness contract: applying `transform-matrix` then `inverse-transform-matrix` (same center) yields unit; this is what lets hit-testing run in untransformed space.
**Probe:** direct census pins: `grep -c 'round-to-zero' common/src/app/common/geom/shapes/transforms.cljc` → 10 covers the solve side; consumer behavior pinned via `points-transform-matrix` test table (rotation rows assert cos/sin matrix form) in geom_shapes_test.cljc; `grep -c 'matrix-str-roundtrip-test' common/test/common_tests/geom_test.cljc` → 1 pins str form round-trip.
**Retrieve (live-resolved rank#2 on the dispatch query):**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"apply-transform dispatch move generic","limit":5,"detail":"ids"}'
```
(route by Source line: `inverse-transform-matrix` resolves :145-165.)

## Verdict
Adopt the sandwich composition and the asymmetric inverse ordering. Adapt precision/format of `transform-str` to your renderer. Omit the FIXME-tagged rect helper placement concerns.
