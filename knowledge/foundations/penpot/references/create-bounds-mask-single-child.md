<!-- capsule-v2 -->
# Bounds of one node — who contributes geometry: the mask, the modifiers, the children?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `penpot`. **Question:** When computing a single shape's (possibly modified) bounds inside the lazy map, which inputs win for groups vs masks vs leaves?

## Mask takes ONE child; modifiers transform; groups merge
**Path/Symbol:** `common/src/app/common/geom/bounds_map.cljc:create-bounds` (:25-57); supporting `common/src/app/common/geom/shapes/points.cljc` (`width-points` :54-57, `height-points` :59-62, `merge-parent-coords-bounds` :161-163).
**Signature:** `(create-bounds shape bounds-map objects)` / `(… modif-tree)` / `(… modif-tree current-ref)` → 4-point bounds vector.
**Data Shape:** in: shape map, either bounds-map (of delays), objects tree, optional modif-tree + old-entry ref; out: `[p0 p1 p2 p3]` points.

### Decisive source
```clojure
(if (cfh/group-shape? shape)
  (let [modifiers (dm/get-in modif-tree [id :modifiers])
        children  (cond->> (cfh/get-immediate-children objects id)
                    (cfh/mask-shape? shape)
                    (take 1))                          ;; masks: FIRST CHILD ONLY
        shape-bounds   (if current-ref @current-ref @(get bounds-map id))
        current-bounds (cond-> shape-bounds
                         (not (ctm/empty? modifiers))
                         (gtr/transform-bounds modifiers))
        children-bounds (->> children
                             (mapv #(deref (get bounds-map (:id %)))))]
    (gpo/merge-parent-coords-bounds children-bounds current-bounds))
  ;; Shape
  (let [shape-bounds (if current-ref @current-ref @(get bounds-map id))]
    (cond-> shape-bounds
      (not (ctm/empty? modifiers))
      (gtr/transform-bounds modifiers))))
```

**Flow:** dispatch on group-ness → for groups: take immediate children (masked group ⇒ `take 1`), deref each child's entry from the SURROUNDING (new) map, transform own current bounds by non-empty modifiers, merge via `merge-parent-coords-bounds` → for leaves: own bounds (+ modifier transform). The three-arity chain defaults modif-tree and current-ref to nil.
**Invariant:** (1) A masked group's bounds are its OWN current bounds merged with exactly ONE child — consistent with the transforms-plane rule that masks adopt first-child geometry (see `group-mask-selrect-regeneration`). (2) Modifier application is gated on `ctm/empty?`, not nil-ness — an EMPTY modifiers map must not trigger a transform. (3) Point-derived width/height clamp at `max 0.01` (`points.cljc`) — zero-sized shapes still yield valid bounds (test-pinned). (4) The bounds value is ALWAYS a 4-point vector, never a rect; rect-ification happens later.
**Probe:** `common/test/common_tests/geom_bounds_map_test.cljc`: `transform-bounds-map-masked-group-test` (two-child masked group builds without error; assertion is smoke-level — caveat recorded), `objects->bounds-map-zero-sized-rect-test` (w/h ≥ 0.01), `transform-bounds-map-move-rect-test` (move (100,200) ⇒ origin exactly (110,220)). Census pins executed this pass: `grep -c "take 1" common/src/app/common/geom/bounds_map.cljc` → 1.
**Retrieve (live-resolved rank#1/#2):**
```
search_graph {project:"penpot", query:"create-bounds mask children merge-parent-coords", limit:5}
→ rank1 shapes.points.merge-parent-coords-bounds :161-163 · #2 shapes.points.parent-coords-bounds :114-159 · render-wasm test_masked_group_bounds_are_mask_bounds :602-630 confirms the SAME rule exists in the Rust twin
```

## Verdict
Adopt the three-way contribution rule (mask=first-child, group=children∪self-modified, leaf=self) and the 0.01 clamps. Adapt `gtr/transform-bounds` to your modifier representation (it consumes the same op-log records as `modif-tree-persistence`). Omit penpot's immediate-children lookup machinery if your tree stores children inline.
