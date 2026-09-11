<!-- capsule-v2 -->
# Wasm constraint twin — how does the Rust renderer approximate constraint propagation, and where exactly does parity with the Clojure editor end?

**Source:** penpot MPL-2.0 `develop@64a52d6b`; Codebase Memory project `penpot`. **Question:** If my renderer needs constraints but cannot afford frame-local intersections, what is the proven axis-aligned approximation — and which behaviors must stay editor-only?

## Path/Symbol
`render-wasm/src/shapes/modifiers/constraints.rs` — `calculate_resize` :5–44, `calculate_displacement` :46–99, `propagate_shape_constraints` :101–167. CLJ counterpart: `common/src/app/common/geom/shapes/constraints.cljc`.
**Signature:**
```rust
fn calculate_resize(ch: ConstraintH, cv: ConstraintV,
    parent_before/after: &Bounds, child_before/after: &Bounds) -> Option<(f32, f32)>
fn calculate_displacement(/* same inputs */) -> Option<(f32, f32)>
fn propagate_shape_constraints(parent_before, parent_after, child_before,
    ch, cv, transform: Matrix, ignore_constrainst: bool) -> Result<Matrix>
```
**Data Shape:** axis-aligned AABBs (`Bounds` exposing nw/ne/sw corners, width/height/left/right/top/bottom), NOT 4-corner transformable point frames; result is a composed `Matrix`.

### Decisive source (entry + fast path + ordering)
```rust
if (ignore_constrainst || constraint_h == ConstraintH::Scale && constraint_v == ConstraintV::Scale)
    || is_move_only_matrix(&transform) { return Ok(transform); }        // :112-117

let mut child_bounds_after = child_bounds_before.transform(&transform);
if let Some((sw, sh)) = calculate_resize(…) { /* scale matrix sandwiched in
   parent transform about child center */ transform.post_concat(&scale); }   // :123-150
if let Some((dx, dy)) = calculate_displacement(… parent_after, child_before, &child_bounds_after) {
   let th = parent_bounds_after.hv(dx);      // horizontal axis vector AFTER
   let tv = parent_bounds_after.vv(dy);
   transform.post_concat(&Matrix::translate(th + tv)); }                  // :153-164
```

**Flow:** three exits in order — ignore/scale/move-only pass the matrix through untouched; then RESIZE first (per-axis factor: Left|Right|Center → `parent_before.width()/max(0.01,parent_after.width())`; LeftRight → target-width arithmetic `(parent_after.width() − left − right)/max(0.01, child_after.width())`) applied via a scale matrix pre/post-concatenated around the parent's own transform about the child center; then DISPLACEMENT recomputed against the ALREADY-SCALED `child_bounds_after` and projected onto the parent-after axis vectors `hv()/vv()`.

**Invariant / parity boundary vs the CLJ plane:**
1. **Axis-aligned only.** No line-line intersection, no rotated parents, no angle/sign algebra — a rotated parent's constraints are computed against its AABB here. The CLJ anchor-intersection and displacement-sign machinery (constraint-anchor-line-intersection.md, constraint-displacement-sign-algebra.md) has NO wasm counterpart; fidelity for rotated parents is editor-only by design.
2. **Move-only fast path is mirrored semantics**: `is_move_only_matrix` ⇔ CLJ `ctm/only-move?` fan-out — both runtimes agree translation needs no constraints.
3. **Scale-before-displace ordering is load-bearing**: displacement measures `current_left` on the scaled bounds (:153–159 uses `&child_bounds_after` mutated at :148), so reordering the two steps double-counts the resize.
4. **Right/Bottom reverse operand order**: Left computes `target − current`, Right computes `current − target` (:60–64) — sign lives in the match arm, not a shared helper.
5. **Same 0.01 denominator clamps** as CLJ (:15,:21,:28,:34) — the degenerate-size vocabulary is cross-runtime.
6. **Center adds half the PARENT delta** (`+ delta_width/2`, :69/:89) instead of intersecting a midline.
7. `None` returns (epsilon-nothing-to-do) skip each matrix concat independently — resize without displacement and vice versa are both valid outcomes.
**Probe:** render-wasm has no direct unit test file cited for this module (test_propagate_shape in modifiers.rs :528–568 exercises the surrounding propagate path). Evidence source-read at this pin; runner block stands (no cargo/clojure execution in this environment).
**Retrieve (live-resolved rank#1–#3 of total 1489):**
```
search_graph {project:"penpot", query:"propagate_shape_constraints calculate_resize calculate_displacement wasm"}
→ rank1 calculate_resize :5-44 · #2 calculate_displacement :46-99 · #3 propagate_shape_constraints :101-167
```

## Verdict
Adopt the twin's shape ONLY for an axis-aligned renderer hot path: pass-through → scale → displace, epsilon-guarded, parent-axis-vector projected. Do NOT port it as your editor's constraint engine — rotated parents need the CLJ intersection/sign plane. Keep the two runtimes' shared invariants (0.01 clamps, move-only fast path, scale-before-displace) pinned by tests on BOTH sides when you port.
