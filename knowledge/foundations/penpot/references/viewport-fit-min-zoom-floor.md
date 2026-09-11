<!-- capsule-v2 -->
# Fit-to-viewport with a zoom floor — when should aspect fitting be abandoned?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `penpot`. **Question:** How do you fit a content rect into a viewport, and what do you do when the implied zoom would go below a floor?

## Aspect-fit first, min-zoom re-anchor second
**Path/Symbol:** `common/src/app/common/geom/align.cljc:adjust-to-viewport` (:125-174).
**Signature:** `(adjust-to-viewport viewport srect)` / `(adjust-to-viewport viewport srect {:keys [padding min-zoom] :or {padding 0 min-zoom nil}})` → rect.
**Data Shape:** viewport/srect are `{:x :y :width :height}` maps; opts optional; returns a NEW rect (input untouched).

### Decisive source
```clojure
;; If min-zoom is specified and the resulting zoom would be below it,
;; return a rect with the original top-left corner centered in the viewport
;; instead of using the aspect-ratio-adjusted rect (which can push coords
;; extremely far with extreme aspect ratios).
(if (and (some? min-zoom)
         (< (/ (:width viewport) (:width adjusted-rect)) min-zoom))
  (let [anchor-x   (:x srect)
        anchor-y   (:y srect)
        vbox-width  (/ (:width viewport) min-zoom)
        vbox-height (/ (:height viewport) min-zoom)]
    (-> adjusted-rect
        (assoc :x (- anchor-x (/ vbox-width 2))
               :y (- anchor-y (/ vbox-height 2))
               :width vbox-width
               :height vbox-height)
        (grc/update-rect :position)))
  adjusted-rect))
```

**Flow:** pad srect symmetrically (x−p, y−p, w+2p, h+2p) → compare aspect ratios `gprop = vw/vh` vs `lprop = lw/lh`: if viewport is WIDER (`>`) stretch width to match and split the surplus as side padding; if NARROWER (`<`) do the same for height; equal → position-only normalization → THEN the floor check: if `viewport.width / fitted.width < min-zoom`, throw away the fitted geometry and emit a box of exactly `viewport/min-zoom` per side, centered on the ORIGINAL (un-padded) srect's top-left corner.
**Invariant:** (1) The two branches are mutually exclusive on `gprop <=> lprop`; the `:else` arm only fires at exact float equality. (2) The floor branch anchors on the UNPADDED input corner — padding is deliberately discarded there; centering uses half the floored box. (3) Zoom is defined as `viewport.width / rect.width` (width-only), not min(w,h) ratios. (4) Padding grows BOTH width and height by exactly `2*padding` before any comparison.
**Probe:** `common/test/common_tests/geom_align_test.cljc` `adjust-to-viewport-test` pins padding acceptance, positivity of results, and that `{min-zoom 0.5}` over a 100×100 rect in 1920×1080 returns a value (smoke level only — the far-coordinate pathology itself is documented in the source comment, not numerically tested; caveat recorded).
**Retrieve (live-resolved rank#1):**
```
search_graph {project:"penpot", query:"adjust-to-viewport min-zoom padding", limit:5}
→ rank1 geom.align.adjust-to-viewport :125-174 · rank3/#4 zoom.cljs zoom-to-fit-all :113-136 / zoom-to-selected-shape :138-163 are the frontend callers
```

## Verdict
Adopt the fit-then-floor ordering and the re-anchor-at-original-corner escape hatch; adopt the width-only zoom definition if you mirror penpot behavior. Adapt `grc/update-rect :position` normalization to your rect type. Omit the SVG-viewbox coupling (none here) — this seam is self-contained.
