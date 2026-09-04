<!-- capsule-v2 -->
# Numeric precision guards — which epsilon does each comparison use, and why do near-zero floats get rounded to exact zero?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** What are the canonical tolerance predicates of this codebase, and where must they be applied before arithmetic (not after)?

## Two epsilons with distinct jobs: 1e-4 snap vs 1e-3 compare
**Path/Symbol:** `common/src/app/common/math.cljc` (`almost-zero?` :192-193, `round-to-zero` :195-200, `close?` :204-209 with `float-equal-precision` 0.001 :202, `clamp` NaN-aware :187-190, `hypot` :167-171); consumers in matrix.cljc (`unit?`, `move?`, `inverse` singular check) and transforms.cljc (`transform-points-matrix` coefficient snapping).
**Signature:** `(almost-zero? n)` `(round-to-zero n)` `(close? a b)` `(close? a b precision)` → boolean / number.
**Data Shape:** `almost-zero?`/`round-to-zero` share the 1e-4 threshold; `close?` defaults to 1e-3 and is the ONLY float equality in tests and matrix comparison.

### Decisive source
```clojure
(defn almost-zero? [num] (< (abs (double num)) 1e-4))

(defn round-to-zero
  "Given a number if it's close enough to zero round to the zero to avoid precision problems"
  [num]
  (if (< (abs num) 1e-4) 0 num))

(defonce float-equal-precision 0.001)
(defn close?
  "Equality for float numbers. Check if the difference is within a range"
  ([num1 num2] (close? num1 num2 float-equal-precision))
  ([num1 num2 precision] (<= (abs (- num1 num2)) precision)))
```

**Flow:** the recovery solve snaps selrect coords AND all six source-matrix coefficients through `round-to-zero` BEFORE multiplying (:192-207 of transforms.cljc — comment names the failure mode: "very close to zero (but not zero) the rounding can mess with the transforms"). Matrix classification uses `almost-zero?`: `move?` treats b/c≈0 and a/d≈1 as translation-only; `unit?` declares identity; `inverse` returns nil when |det| is almost-zero. Test assertions never use `=` on floats — always `mth/close?`.
**Invariant:** (1) Snap-BEFORE-arithmetic is load-bearing: rounding AFTER the solve leaves det polluted by ±1e-5 ghosts and produces visibly skewed shapes. (2) The two epsilons are NOT interchangeable: widening `close?` to 1e-4 makes matrix comparisons flaky, narrowing `almost-zero?` to 1e-6 resurrects the ghost-det bug. (3) `clamp` is NaN-routing (NaN→from), matching the degrade-don't-throw doctrine of safe-size-rect.
**Probe:** direct census pins (no dedicated test file for math.cljc — behavior is pinned THROUGH its consumers): `grep -c 'almost-zero?' common/src/app/common/geom/matrix.cljc` → 5 ; `grep -c 'defn close?' common/src/app/common/math.cljc` → 1 ; `grep -c 'round-to-zero' common/src/app/common/geom/shapes/transforms.cljc` → 10 ; consumer test `matrix-str-roundtrip-test` in geom_test.cljc exercises close?-based round-trip equality.
**Retrieve (live-resolved rank#1/#2):**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"almost-zero round-to-zero close precision guards","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the two-epsilon vocabulary and the snap-before-solve placement verbatim. Adapt thresholds only with a full consumer audit. Omit the JS/CLJ interop shims inside the functions (#?(:cljs js/Math…) bodies) — platform plumbing.
