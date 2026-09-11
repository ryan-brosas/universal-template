<!-- capsule-v2 -->
# Fixed-constraint resize sandwich + deformation pre-strip — what does "pinned on both edges" compile to, and why are pending modifiers cancelled first?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `penpot`. **Question:** When a parent resize would stretch a child whose `:leftright`/`:topbottom` says both edges stay put, what exact op sequence grows the child instead — and what must happen to the child's in-flight modifiers before constraint deltas compose?

## Path/Symbol
`common/src/app/common/geom/shapes/constraints.cljc` — `constraint-modifier :fixed` :194–227, `normalize-modifiers` :266–290 (docstring :267); helpers `side-vector-resize` :168–172, `gtr/calculate-selrect`/`calculate-transform`, `gmt/inverse`.

**Signature:**
- `(constraint-modifier :fixed axis child-before parent-before child-after parent-after) → modifiers` (resize + move ops)
- `(normalize-modifiers constraints-h constraints-v modifiers child-bounds transformed-child-bounds parent-bounds transformed-parent-bounds) → modifiers`

### Decisive source (the :fixed method, condensed)
```clojure
;; grow the CURRENT side by start+end displacements, then…
(let [before-vec    (side-vector axis child-points-after)
      after-vec     (side-vector-resize axis child-points-after disp-start disp-end)
      scale         (/ (gpt/length after-vec) (mth/max 0.01 (gpt/length before-vec)))
      resize-origin (gpo/origin child-points-after)
      center        (gco/points->center parent-points-after)
      selrect       (gtr/calculate-selrect   parent-points-after center)
      transform     (gtr/calculate-transform parent-points-after center selrect)
      transform-inverse (when (some? transform) (gmt/inverse transform))]
  (-> (ctm/empty)
      (ctm/resize (get-scale axis scale) resize-origin transform transform-inverse)
      (ctm/move disp-start)))
```
(constraints.cljc :208–227; comments at :212–214 state the intent: scale by the grown-side ratio and translate by the start displacement so left+top stays constant.)

**Flow:** `:fixed` = BOTH edges pinned ⇒ when the parent's span between the pinned edges changes, the child must be STRETCHED to bridge it: measure current side length (`before-vec`), measure it again with both displacements applied (`side-vector-resize`), take the ratio (denominator clamped `max 0.01`), emit a per-axis resize about the child's own origin wrapped in the PARENT's transform/inverse, then a move by `disp-start`. Separately, `normalize-modifiers` runs BEFORE any constraint method (calc-child-modifiers :333–338): for every non-:scale axis it CANCELS the deformation already applied to the child by the parent resize — resize by `width(before)/max(0.01,width(after))` about the transformed child origin, inside the CHILD's own selrect transform/inverse (:271–290). :scale axes keep factor 1 because they want the inherited stretch.

**Invariant:** (1) Two different transforms wrap the two steps: normalize uses the CHILD's frame (undo its deformation), the :fixed resize uses the PARENT's frame (re-express growth in parent space) — swapping them is the classic porting bug. (2) `:fixed` is GROWTH, not immobility: immobility-with-resize is what :start/:end produce via plain moves. (3) The 0.01 denominator clamp appears in BOTH steps (normalize :276/:280, fixed :215) — same degenerate-size vocabulary as bounds/width clamps. (4) `transform-inverse` is computed only `when (some? transform)` — singular matrices degrade to nil rather than throwing. (5) Order is mandatory: normalize FIRST (clean slate), then per-axis constraint ops COMPOSE onto the normalized modifiers via `ctm/add-modifiers` (:359–361).
**Probe:** No direct test covers :fixed or normalize numerics; the module's single test pins only `:default` arity. Source-only evidence; port check: parent 100→140 wide, child :leftright at x=20 w=60 ⇒ expect width 100 (=60+20+20) and x unchanged. Runner block stands (no clojure CLI).
**Retrieve (live-resolved):**
```
search_graph {project:"penpot", query:"constraint-modifier fixed resize origin transform-inverse move", file_pattern:"*shapes/constraints*"}
→ rank1 constraint-modifier (multimethod node) · #2 side-vector-resize :168-172
search_graph {project:"penpot", query:"normalize modifiers remove deformation resizing parent"} (broad)
→ normalize-modifiers :266-290 named rank#2 of total 536
```

## Verdict
Adopt the two-phase shape: cancel inherited deformation per non-inherited axis, THEN compose constraint ops. Adapt which axes "inherit" (here :scale) to your vocabulary. Omit nothing from the double 0.01 clamp or the nil-inverse degradation.
