<!-- capsule-v2 -->
# Align to a rotated parent — how do you project an alignment delta onto parent-local axes?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `penpot`. **Question:** When aligning a shape against a *rotated* parent, why does the delta have to become vectors before moving — and where exactly does that happen?

## Parent-space wrapper + axis-vector delta projection
**Path/Symbol:** `common/src/app/common/geom/align.cljc` (`align-to-rect` :21-32, `align-to-parent` :34-49, `calc-align-pos` :51-76); `common/src/app/common/geom/shapes/points.cljc` (`start-hv` :26-31, `start-vv` :40-45).
**Signature:** `(align-to-parent shape parent axis)` → shape' ; `(calc-align-pos wrapper-rect rect axis)` → `{:x … :y …}` ; `(start-hv points val)` / `(start-vv points val)` → point (vector).
**Data Shape:** shape/parent are full shape maps; parent carries `:points` (4-tuple p0..p3), `:transform-inverse`, `:selrect`. Returns a moved shape; nothing mutates.

### Decisive source
```clojure
(defn align-to-parent
  [shape parent axis]
  (let [parent-bounds (:points parent)
        wrapper-rect
        (-> (gsh/transform-points (:points shape) (gsh/shape->center parent) (:transform-inverse parent))
            (grc/points->rect))

        align-pos (calc-align-pos wrapper-rect (:selrect parent) axis)

        xv   #(gpo/start-hv parent-bounds %)
        yv   #(gpo/start-vv parent-bounds %)

        delta (-> (xv (- (:x align-pos) (:x wrapper-rect)))
                  (gpt/add (yv (- (:y align-pos) (:y wrapper-rect)))))]
    (gsh/move shape delta)))
```

**Flow:** transform shape corner points into PARENT space (center pivot + parent's transform-inverse) → collapse to wrapper rect in that space → pure six-axis alignment arithmetic (`calc-align-pos`, case over `:hleft/:hcenter/:hright/:vtop/:vcenter/:vbottom`) yields a target `{x y}` in the SAME space → scalar deltas `(target − wrapper)` per axis → each scalar is scaled onto the parent's own unit edge vector (`start-hv` = along p0→p1, `start-vv` = along p0→p3) → the two vectors add into ONE world-space delta → single `gsh/move`.
**Invariant:** (1) Alignment math is always AABB-of-wrapper math done in the frame whose axes it references — never on raw `:x/:y` fields of rotated shapes. (2) The final move is ONE translation composed from projected components; projecting AFTER composing (`(gpt/point dx dy)` then rotate) is the wrong-port this guards. (3) `align-to-rect` (:21-32) is the unrotated special case: same calc, plain `(gpt/point dx dy)`. (4) `valid-align-axis` (:16-17) is the closed six-symbol set — dispatch via `case` throws on anything else.
**Probe:** `common/test/common_tests/geom_align_test.cljc` `calc-align-pos-test` pins all six axes numerically (e.g. `:hcenter` of wrapper w=100 in rect x=200 w=400 → pos.x=350). NOTE: no direct test exercises the rotated-parent projection path itself — coverage caveat; the projection's correctness rests on `points.cljc` unit-vector semantics read directly.
**Retrieve (live-resolved rank#1/#2/#5):**
```
search_graph {project:"penpot", query:"align-to-parent calc-align-pos start-hv", limit:5}
→ rank1 geom.align.calc-align-pos :51-76 · rank2 geom.align.align-to-parent :34-49 · rank5 shapes.points.start-hv :26-31
```

## Verdict
Adopt the inverse-space wrapper computation and the axis-vector delta projection; adopt `calc-align-pos` verbatim as a pure six-case function. Adapt the vector primitives to your geometry library (any unit-edge-vector × scalar works). Omit penpot's `gsh/move` group-cascade semantics if your tree has different reparenting rules.
