<!-- capsule-v2 -->
# Constraint gating ladder — when does a child get full constraint math, and when do fast paths skip it?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `penpot`. **Question:** Per parent/child pair, which of the five exit paths applies — no-op, move-fan-out, scale-pass-through, layout early-return, axis-aligned reset, or the full pipeline — and what state does each need?

## Path/Symbol
`common/src/app/common/geom/shapes/constraints.cljc` (`calc-child-modifiers` :292–361); consumers in `common/src/app/common/geom/modifiers.cljc` — `set-modifiers-constraints` :137–151, `set-children-modifiers` :36–65, `propagate-modifiers-constraints` :190–194, called from `set-objects-modifiers` :368.

**Signature:** `(calc-child-modifiers parent child modifiers ignore-constraints child-bounds parent-bounds transformed-parent-bounds) → modifiers` — note the LAST arg is a DELAY.
**Data Shape:** modif-tree `{id {:modifiers {bucket ops}}}` (bucket model: modifiers-four-bucket-record.md); bounds are delay-wrapped 4-point vectors from the pass-4 bounds map.

### Decisive source
```clojure
(let [transformed-parent-bounds @transformed-parent-bounds   ;; :322 deref INSIDE branch
      reset-modifiers?
      (and (gpo/axis-aligned? parent-bounds)
           (gpo/axis-aligned? child-bounds)
           (gpo/axis-aligned? transformed-parent-bounds)
           (not= :scale constraints-h) (not= :scale constraints-v))
      modifiers (if reset-modifiers?
                  (ctm/empty)
                  (normalize-modifiers …))
      …]
  ;; layout parents stop right after normalize:
  (if (and (ctl/any-layout? parent) (not (ctl/position-absolute? child)))
    modifiers
    (… constraint-modifier per axis, ctm/add-modifiers …)))
```
(constraints.cljc :322–361; comment :345–346: "If the parent is a layout we don't need to calculate its constraints. Finish after normalize the children (to keep proper proportions)".)

**Flow / the five exits, outermost first:**
1. **Consumer guards** (set-modifiers-constraints :149–151): propagate only when the parent's modifiers have CHILD-bucket ops (`child-modifiers?`), parent is group-like/frame, and parent ≠ root. Root frames never propagate.
2. **Move fan-out** (set-children-modifiers :41–46): `only-move?` modifiers (no structure, every op `:move`) copy VERBATIM to all children — translation needs no constraints. This mirrors the Rust twin's `is_move_only_matrix` pass-through.
3. **Both-scale** (:319–320): `:scale + :scale` returns child modifiers untouched before ANY deref or geometry work.
4. **Layout early-return** (:302–303, :347–348): flex/grid-layout parent with non-absolute child forces constraints to `:left/:top`, normalizes proportions, then RETURNS — placement belongs to the layout propagation phase (propagate-modifiers-layouts runs later in set-objects-modifiers :374).
5. **Axis-aligned reset** (:326–335): if parent, child, AND transformed-parent bounds are all axis-aligned and neither axis is `:scale`, pending child modifiers are DISCARDED (`ctm/empty`) and recomputed from raw bounds — composing would double-apply deformation normalize just removed.

**Invariant:** (1) `transformed-parent-bounds` arrives as a delay and is deref'd at :322 only inside the non-scale branch — children that take exits 3 never force the parent's transformed bounds to realize (continuation of the pass-4 laziness contract). (2) Constraint resolution reads `(:constraints-h child (default-constraints-h child))` with `ignore-constraints` forcing BOTH axes to `:scale` (user opt-out). (3) The reset path exists because normalize-modifiers assumes it starts from a clean slate in axis-aligned space; rotated geometry composes instead. (4) Exits are ordered cheap→expensive; port them in this order or the lazy-deref guarantee breaks.
**Probe:** geom_bounds_map_test.cljc (pass 4) pins the laziness semantics this relies on; geom_shapes_constraints_test.cljc pins only `:default` arity. Consumer provenance from source: `set-objects-modifiers` :368 `(propagate-modifiers-constraints objects bounds-map ignore-constraints modif-tree shapes-tree-all)` between the first bounds rebuild (:370–371 follows it). Runner block stands (no clojure CLI).
**Retrieve (live-resolved rank#1, named hits):**
```
search_graph {project:"penpot", query:"calc-child-modifiers ignore-constraints layout position-absolute scale"}
→ rank1 calc-child-modifiers :292-361 (of total 1120); named hits: position-absolute? layout.cljc :538-543,
   set-modifiers-constraints :137-151 (#24), propagate-modifiers-constraints :190-194 (#25), select-child types/modifiers.cljc :552-554
```

## Verdict
Adopt the ordered exit ladder with lazy parent-state deref — it is what keeps O(children) work proportional to actual modification depth. Adapt guard predicates to your shape taxonomy; keep "layout parents own placement, constraints only fix proportions" as a hard separation. Graph caveat: inbound CALLS edges unresolved for calc-child-modifiers (callers_total=0); consumer chain confirmed from source reads.
