<!-- capsule-v2 -->
# Safe sizing — how do you resize shapes whose stored geometry is broken?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory `mnt-hdd-utopia-inspo-external-penpot` (re-pinned from stuck `ext-penpot` @dd6b521b — modifiers.cljc byte-stable, spans verified :122-147/:444-512). **Question:** When a shape's `:selrect`/points are NaN, zero, or missing (corrupted by old bugs/imports), what is the defensive ladder that still yields a usable scale vector?

## Connected graph-selected seam
**Path/Symbol:** `common/src/app/common/types/modifiers.cljc` : `safe-size-rect?` predicate (:122-132) / `safe-size-rect` (:134-147) + consumers `change-size` (:444-452), `change-dimensions-modifiers` (:454-486), `change-orientation-modifiers` (:488-512); terminal fallback `grc/empty-rect` = (0,0,0.01,0.01) (`common/src/app/common/geom/rect.cljc`:39/:117).
**Signature:** `(safe-size-rect shape) → rect` (never nil, never invalid) · `(change-dimensions-modifiers shape attr value {:keys [ignore-lock?]}) → modifiers`.
**Data Shape:** candidate rects tried in fixed order; each must pass finite+positive+≤`sm/max-safe-int` on BOTH width and height.

### Decisive source
```clojure
(defn safe-size-rect
  "Returns the best available size rect for a shape, trying several
   fallbacks in order:
   1. `:selrect`  — if it has valid, in-range, positive dimensions.
   2. `points->rect` — computed from the shape's corner points.
   3. Top-level `:x :y :width :height` shape fields.
   4. `grc/empty-rect` — a unit rect (0,0,0.01,0.01) of last resort."
  [{:keys [selrect points x y width height]}]
  (or (and ^boolean (safe-size-rect? selrect) selrect)
      (let [from-points (grc/points->rect points)]
        (and ^boolean (safe-size-rect? from-points) from-points))
      (let [from-shape (grc/make-rect x y width height)]
        (and ^boolean (safe-size-rect? from-shape) from-shape))
      grc/empty-rect))
```

**Flow:** every dimension change derives its scale as requested/safe-current where current = `safe-size-rect` output → values below 0.01 clamp to 0.01 (`value (if (< (mth/abs value) 0.01) 0.01 value)`, comment "Avoid having shapes with zero size") so scale never divides by ~zero → `proportion-lock` recomputes the OTHER axis via stored `:proportion` unless `ignore-lock?` (width drives height ÷proportion; height drives width ×proportion :470-476). Orientation swaps reuse the same safe dims and pre-map their origin through the shape's transform when present.
**Invariant:** a resize modifier built against a fallback rect is still CORRECT because scale = target/current — the ratio self-corrects even when the absolute size was garbage. Never trust `:selrect` blindly; the unit-rect last resort exists so the pipeline degrades to "tiny but valid" instead of NaN-poisoning the document — and the floor is TWO-SIDED: `make-rect` clamps any constructed rect to ≥0.01 (`mth/max width 0.01`, rect.cljc :67-68). Ladder order is trust order — reordering changes results on partially-corrupt shapes.
**Probe:** direct test `safe-size-rect-fallbacks` in common/test/common_tests/types/modifiers_test.cljc (:183-247) pins ALL FOUR rungs incl rung-3 (selrect+points nilled→top-level fields) and rung-4 (all nilled→scale (/ 200 0.01)); census pins: `grep -cF '(safe-size-rect shape)' common/src/app/common/types/modifiers.cljc` → 4 call sites · `grep -cF 'grc/empty-rect' <same>` → 2 · `grep -c 'close? 0.01' common/test/common_tests/geom_shapes_test.cljc` → 2 (resize-to-zero yields w=h=0.01).
**Retrieve (live-resolved rank#1/#2):**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"safe-size-rect fallback empty-rect","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the four-rung validated-fallback ladder for any document model with historical/corrupt payloads; adapt threshold (`max-safe-int` guard blocks Infinity); omit proportion-lock if your objects have no aspect ratio. Test anchors executed: `change-dimensions-modifiers-value-clamping` (0.001→0.0001 exact), `change-orientation-zero-*-selrect-does-not-throw` trio (:663-691), `safe-size-rect-fallbacks` (31 deftests in file; runner blocked honestly — JVM deps absent in inspo clone).
