<!-- capsule-v2 -->
# Constraint anchors as line intersections — why do :start/:end/:center constraints survive ROTATED parents?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `penpot`. **Question:** How do I compute "distance from child edge to parent edge" so it stays correct when the parent is rotated, without any trig-by-hand?

## Path/Symbol
`common/src/app/common/geom/shapes/constraints.cljc` — `right-vector` :68–74, `left-vector` :76–83, `top-vector` :85–92, `bottom-vector` :94–101, `center-horizontal-vector` :103–116, `center-vertical-vector` :118–130, axis dispatchers `start-vector`/`end-vector`/`center-vector` :132–148.

**Signature:** `(right-vector child-points parent-points) → vector-point` where points are the 4-corner `[p0 p1 p2 p3]` vectors and the result is a `gpt` point usable as a VECTOR (child corner → intersection).
**Data Shape:** parent corners `[p0 p1 p2 p3]` = top-left, top-right, bottom-right, bottom-left in PARENT-LOCAL frame (post parent-transform-inverse); child corners same order. All math flows through `gpt/to-vec`, `gpt/add`, `gsi/line-line-intersect`.

### Decisive source
```clojure
(defn right-vector
  [child-points parent-points]
  (let [[p0 p1 p2 _] parent-points
        [_c0 c1 _ _] child-points
        dir-v (gpt/to-vec p0 p1)
        cp (gsi/line-line-intersect c1 (gpt/add c1 dir-v) p1 p2)]
    (gpt/to-vec c1 cp)))
```
(constraints.cljc :68–74; left uses child c3 against side p0→p3; top uses c0 against p0→p1 along direction p0→p3; bottom uses c2.)

**Flow:** for a "keep my right edge pinned to the parent's right side" constraint: take the child's top-right corner `c1`, shoot a ray from it PARALLEL to the parent's top edge (`dir-v = p0→p1`), intersect with the parent's RIGHT side segment (`p1→p2`), return `c1 → intersection`. The intersection point is expressed in the parent's own coordinate frame — both point sets were mapped through `gpo/parent-coords-bounds` before this code runs (calc-child-modifiers :349–350). Center constraints build a midline first: `p1c = p0 + 0.5·dir-v`, `p2c = p3 + 0.5·dir-v`, then intersect the child ray with that midline (:111–114).

**Invariant:** (1) NO scalar deltas and NO trig — rotation-safety comes entirely from doing the ray/segment intersection inside the parent's frame; porting this as `(- parent-right child-right)` on x/y fields silently breaks under rotation. (2) The ray is parallel to ONE parent edge while the target side is spanned by the OTHER edge direction — that cross-axis pairing is what makes the four functions non-interchangeable (top/bottom shoot along p0→p3 and land on p0→p1/p2→p3). (3) Axis dispatch is table-of-functions, not case analysis: `(start-vector axis …)` picks `left-vector` for :x, `top-vector` for :y (:132–137). (4) These functions are pure geometry — they never touch modifiers; the displacement they feed into is sign-corrected separately (see constraint-displacement-sign-algebra.md).
**Probe:** No direct test exercises the *-vector family (geom_shapes_constraints_test.cljc contains only the `:default` arity pin). Source-only evidence; verify by porting the invariant: rotate a parent 30°, resize it, and check a :right-constrained child's edge distance to the rotated right side stays constant. Runner block stands: no clojure CLI here — tests read, not executed.
**Retrieve (live-resolved rank#1–#4):**
```
search_graph {project:"penpot", query:"line-line-intersect anchor vector parent edge rotated", file_pattern:"*shapes/constraints*"}
→ rank1 right-vector :68-74 · #2 left-vector :76-83 · #3 top-vector :85-92 · #4 bottom-vector :94-101 (start/end/center dispatchers :132-148 named)
```

## Verdict
Adopt the frame-local ray/segment intersection as THE way to measure constrained distances under arbitrary parent transforms. Adapt corner-index conventions to your point ordering but keep the cross-axis ray pairing. Omit per-axis duplication by keeping the function-table dispatch.
