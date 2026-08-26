<!-- capsule-v2 -->
# Displacement sign algebra — how is a constraint move derived from before/after anchor vectors, and when does it flip?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `penpot`. **Question:** Given the same child corner measured against its parent before and after a resize, what exact translation restores the constraint — including when the parent flipped or rotated past perpendicular?

## Path/Symbol
`common/src/app/common/geom/shapes/constraints.cljc` — `displacement` :150–160, `side-vector` :162–166, `side-vector-resize` :168–172; supporting `gpt/angle-with-other` (`common/src/app/common/geom/point.cljc` :261–280).

**Signature:** `(displacement before-v after-v before-parent-side-v after-parent-side-v) → move-point`
**Data Shape:** all four args are `gpt` points used as free vectors; parent side vectors come from `side-vector` (axis :x → c0→c1, axis :y → c0→c3 of the PARENT's corners).

### Decisive source
```clojure
(defn displacement
  [before-v after-v before-parent-side-v after-parent-side-v]
  (let [before-angl (gpt/angle-with-other before-v before-parent-side-v)
        after-angl  (gpt/angle-with-other after-v after-parent-side-v)
        sign   (if (mth/close? before-angl after-angl) 1 -1)
        length (* sign (gpt/length before-v))]
    (if (mth/almost-zero? length)
      after-v
      (gpt/subtract after-v (gpt/scale (gpt/unit after-v) length)))))
```
(constraints.cljc :150–160.)

**Flow:** keep the BEFORE magnitude, adopt the AFTER direction: result = after_v − unit(after_v)·(sign·|before_v|). The move is expressed along where the anchor NOW points, at the length it USED to be. Sign: compare the unsigned angle between (anchor, parent-side) pairs before vs after — equal within `mth/close?` (1e-3 regime) ⇒ +1, otherwise −1. Because `angle-with-other` is UNSIGNED (acos of clamped normalized dot product, NaN→0, zero-length inputs → angle 0), the only flip witness available is this before/after comparison.

**Invariant:** (1) Direction must come from AFTER: reusing the before direction breaks whenever the parent rotated or mirrored between snapshots — the anchor now points somewhere else. (2) The −1 branch encodes "the child crossed to the other side of its target side" (e.g. flipping a parent); magnitude alone cannot express that. (3) Degenerate guard: |before| ≈ 0 → return `after-v` unchanged (no snap-to-zero); uses `almost-zero?` (1e-4 regime per numeric-precision-guards.md). (4) `angle-with-other` clamps its cosine to [−1,1] BEFORE acos and maps NaN → 0 — port both guards or antiparallel inputs throw. (5) All four `constraint-modifier` methods (:start/:end/:center/:fixed) route through this one function with axis-appropriate vectors; :fixed calls it TWICE (start+end) and feeds both into a resize instead of a plain move.
**Probe:** No direct test covers `displacement` numerics (test file holds only the `:default` arity pin). Source-only evidence; port check: rotate a parent 180° about x so the child's :top anchor inverts, verify sign flips and the child stays glued. Runner block stands (no clojure CLI).
**Retrieve (live-resolved rank#1/#2):**
```
search_graph {project:"penpot", query:"displacement angle sign flip before after", file_pattern:"*shapes/constraints*"}
→ rank1 displacement :150-160 · #2 get-displacement :49-56
```

## Verdict
Adopt "before-magnitude × after-direction × compared-angle sign" for any relative-position restore across two snapshots of a transformed frame. Adapt the epsilon regimes to your precision vocabulary (keep 1e-4 no-op / 1e-4 unit-guard split). Omit nothing — the guards are load-bearing.
