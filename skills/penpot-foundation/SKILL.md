---
name: penpot-foundation
description: "Use when building or porting a collaborative visual editor's core data model: accumulating undoable edits against a large shape/document map, applying transforms as ordered op logs, persisting huge maps field-by-field, or keeping geometry math identical across two language runtimes (JVM/JS). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# penpot: document-model foundations

## Use this for
Use when building or porting a collaborative visual editor's core data model: accumulating undoable edits against a large shape/document map, applying transforms as ordered op logs, persisting huge maps field-by-field, or keeping geometry math identical across two language runtimes (JVM/JS). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/changes-builder-dual-ledger.md` — how to accumulate one atomic edit carrying redo steps + exact inverse undo steps + a live working copy of file-data.
- `references/changes-processor-two-phase.md` — how ~40 heterogeneous change types reduce onto one immutable file-data map with a bound-scoped touched second phase.
- `references/modifiers-oplog-builders.md` — how live drag operations compose into an ordered, mergeable op log that stays cheap during interaction.
- `references/modifiers-matrix-application.md` — how an op log folds into ONE affine matrix, including resize-with-pre-transform on rotated shapes.
- `references/safe-size-rect-ladder.md` — how to resize shapes whose stored geometry is corrupted (four-rung validated fallback).
- `references/objects-map-lazy-codec.md` — a UUID→object map that decodes lazily and encodes only dirty fields for per-field persistence.
- `references/undo-stack-bounded.md` — minimal bounded undo/redo stack (100 entries) with branch discard and duplicate suppression.
- `references/shape-tree-structure-guards.md` — reparent/delete guards: descendant-set cycle blocking, component-copy rules, subtree cascades.
- `references/data-helpers-sentinel-updates.md` — sentinel-guarded conditional path updates (absence ≠ nil) powering idempotent change replays.
- `references/uuid-v8-identity.md` — time-sortable v8 identity across JVM/JS with deterministic fakes for tests.
- `references/geometry-kernel-point-matrix.md` — one Point/Matrix record pair over two runtimes with epsilon-only float equality.
- `references/file-migrations-registry-kernel.md` — how a document declares which data migrations already ran and what applies the rest.
- `references/file-migrations-repair-idiom.md` — the repair-migration shape: predicate gate, strip-then-seed, try/catch-to-original idempotence.
- `references/update-objects-tree-protocol.md` — one result-triple visitor (`:keep/:update/:remove`) walking pages AND component copies.
- `references/features-compatibility-ladder.md` — feature-set taxonomy plus directional-difference compatibility checks with named error codes.
- `references/file-data-metadata-envelope.md` — per-blob metadata envelope surviving db/storage/legacy backends via merge/strip discipline.
- `references/binfile-manifest-provenance.md` — persisting archive-manifest provenance onto imported files with legacy-key fallback.
- `references/workspace-stats-audit-event.md` — one enriched stats audit event per workspace open, emitted after async deps settle.
- `references/error-hygiene-hardening.md` — stripping internal fields from 500 bodies while keeping curated hints; SQLSTATE→copy table.
- `references/session-authz-logout-invalidation.md` — dual-token-version session resolution, renewal window, and server-side logout deletion.
- `references/file-data-backend-switch.md` — row-keyed read dispatch + config-keyed write dispatch for a safe storage-backend flip.
- `references/affine-recovery-corners.md` — reconstructing the affine matrix from four transformed corner points (closed-form solve with structurally-dead terms).
- `references/transform-dispatch-move-vs-generic.md` — why pure translation takes a different application path than any other transform, and the flip dot-product algebra.
- `references/modifiers-four-bucket-record.md` — the ordered four-bucket op log (geometry/structure × parent/child) with head-merge and zero-op elision.
- `references/group-mask-selrect-regeneration.md` — recomputing container bounds from transformed children without double-applying the group transform; mask adopts first child.
- `references/modif-tree-persistence.md` — id→modifiers map with dissoc-on-empty semantics and projected structure-child fan-out to descendants.
- `references/numeric-precision-guards.md` — two-epsilon vocabulary (1e-4 snap vs 1e-3 compare) and snap-BEFORE-arithmetic placement.
- `references/point-transform-convention.md` — row-vector point application and AABB-midpoint centers that the whole stack assumes.
- `references/transform-matrix-pair.md` — composing rotation+flip+transform into one render matrix, and why its inverse mirrors the body order.
- `references/convenience-modifier-builders.md` — foreign-center rotation compensation, dimension clamping, proportion-lock, orientation swaps as primitive ops.
- `references/transform-shape-entry.md` — the single funnel: strip modifiers, compile, apply; root exemption split between geometry and structure.
- `references/align-parent-axis-projection.md` — aligning against a rotated parent: wrapper rect in parent space, scalar delta projected onto parent-local axis vectors before one move.
- `references/distribute-space-unit-interval.md` — equal-gap distribution: center-sort, unit = free/(n−1), single forward reposition loop anchored at both extremes.
- `references/viewport-fit-min-zoom-floor.md` — aspect-ratio fit with symmetric padding, then a min-zoom floor that abandons the fit and re-anchors at the original corner.
- `references/bounds-map-delay-volatile-propagation.md` — lazy `{id delay}` bounds map whose delays close over a volatile holding the NEW map, so group bounds see children's modified geometry.
- `references/create-bounds-mask-single-child.md` — per-node bounds rule: masks take one child, groups merge children∪self-modified, leaves self; 0.01 clamps on degenerate sizes.
- `references/grid-generic-algebra.md` — one `[size item-length next-v gutter]` calculator behind column/row/square grids with ordered derivations and a stretch-gutter max(0,…)+NaN ladder.
- `references/snap-point-vocabulary.md` — snap candidate tiers (rect corners+center ⊂ frame midpoints), tri-conditional guide suppression, display-gated axis-filtered grid lines.
- `references/constraints-vocabulary-defaults.md` — 8 stored constraints reduce to 4 behaviors; tree-position-derived defaults never persisted.
- `references/constraint-anchor-line-intersection.md` — rotation-safe :start/:end/:center anchors via frame-local ray/segment intersection.
- `references/constraint-displacement-sign-algebra.md` — before-magnitude × after-direction restore with compared-angle flip sign and degenerate no-op guard.
- `references/fixed-constraint-resize-sandwich.md` — :leftright/:topbottom compiles to grow-by-both-displacements resize + start move, after a per-axis deformation pre-strip.
- `references/calc-child-constraint-gates.md` — five ordered exits (guards → move fan-out → scale pass-through → layout early-return → axis-aligned reset) with lazy parent-bounds deref.
- `references/wasm-constraint-twin-axis-aligned.md` — Rust renderer's AABB approximation: pass-through/scale/displace pipeline and its exact parity boundary vs the Clojure editor.

## Capsule map
- **Change system** — `changes-builder-dual-ledger`: redo vector + reversed undo list; metadata-mounted working state read by later builders.
- **Change system** — `changes-processor-two-phase`: pure multimethod fold + bound-scoped touched-changes drain.
- **Transform engine** — `modifiers-oplog-builders`: monotonic order counter, tail-merge of same-type ops, zero-op elision.
- **Transform engine** — `modifiers-matrix-application`: sorted single-matrix funnel; local-frame resize sandwich T(origin)·S·T(−origin) wrapped in shape transform/inverse.
- **Transform engine** — `safe-size-rect-ladder`: selrect→points→fields→unit-rect fallback so scale ratios self-correct against corrupt geometry.
- **Storage** — `objects-map-lazy-codec`: dual-map decode-on-read/negative-cache, tombstone-assoc, compact-on-persist via fressian/transit tags.
- **History** — `undo-stack-bounded`: index-cursor stack; append truncates redo branch then evicts oldest under MAX-UNDO-SIZE=100.
- **Scene tree** — `shape-tree-structure-guards`: cycle-proof reparenting, dual-parent copy checks, cascade delete before parent-vector edit.
- **Primitives** — `data-helpers-sentinel-updates`: identical?-sentinel conditional updates; transient concat fast paths.
- **Primitives** — `uuid-v8-identity`: native platform UUIDs, time-ordered next(), atom-counter fakes via with-redefs.
- **Primitives** — `geometry-kernel-point-matrix`: reader-conditional math, nil-as-identity multiply (pure) vs in-place (!) JS twin, singular-safe inverse.
- **File migrations** — `file-migrations-registry-kernel`: ordered-set ledger on the file; version-seeding for legacy files; fold-once with ::migrated metadata.
- **File migrations** — `file-migrations-repair-idiom`: predicate-gated strip-then-seed repairs, total over garbage, idempotent, try/catch-to-original.
- **File migrations** — `update-objects-tree-protocol`: result-triple visitor over pages + components; container context via shape metadata; delete stops recursion.
- **Compatibility** — `features-compatibility-ladder`: supported/default/frontend-only/backend-only/no-migration sets; directional diff checks with named codes.
- **Persistence** — `file-data-metadata-envelope`: open optional-key metadata map; storage pointer written once and stripped elsewhere; shared decoder.
- **Persistence** — `binfile-manifest-provenance`: manifest schema → config-carried context → per-file stamping with `:refer` legacy fallback; strip on export.
- **Telemetry** — `workspace-stats-audit-event`: single-pass stats (deleted-excluded components, self-inclusive libraries −1 clamped) emitted once after `::all-libraries-resolved`.
- **HTTP errors** — `error-hygiene-hardening`: dissoc :state/:path/:context from 500s; curated-vs-raw hint regimes; SQLSTATE→fixed copy with generic fallback.
- **Sessions** — `session-authz-logout-invalidation`: ver 0/1 token ladder; 6h renewal window cookie-only; logout deletes the DB row then clears the cookie.
- **Persistence** — `file-data-backend-switch`: reads dispatch on the row's stored backend, writes on config default — flipping the default is not a row migration.
- **Transform engine** — `affine-recovery-corners`: closed-form corner→matrix solve; dead mb4/mb6 terms are load-bearing structure, not cleanup targets; unit result normalizes to the shared base constant.
- **Transform engine** — `transform-dispatch-move-vs-generic`: `move?`-keyed dispatch keeps translation cheap; flips re-derive from edge-vector dot products and negate rotation only when exactly one axis flipped.
- **Transform engine** — `modifiers-four-bucket-record`: Modifiers[geometry/structure × parent/child] with global `last-order`; consecutive same-type ops merge at head; rotation is deliberately dual-bucket.
- **Transform engine** — `group-mask-selrect-regeneration`: children→inverse-transform→AABB→re-transform round trip; masks adopt first-child geometry; regeneration clears flip flags.
- **Transform engine** — `modif-tree-persistence`: `{id {:modifiers …}}` with dissoc-on-cancel; structure-child ops fan out to descendants via projection only.
- **Primitives** — `numeric-precision-guards`: `almost-zero?`/`round-to-zero` (1e-4) snap coefficients before solving; `close?` (1e-3) is the only float equality; clamp routes NaN.
- **Primitives** — `point-transform-convention`: row-vector application (`x' = x·a + y·c + e`) and AABB-midpoint centers are load-bearing conventions behind every rotation.
- **Transform engine** — `transform-matrix-pair`: render matrix = translate(center)·transform·flip-scales·translate(−center); inverse composes flips BEFORE transform-inverse.
- **Transform engine** — `convenience-modifier-builders`: foreign-center rotation = geometric spin + compensating move; dimension requests clamp to 0.01 then honor proportion-lock.
- **Transform engine** — `transform-shape-entry`: strip `:modifiers` → compile → apply; root skips geometry but not structure; empty modifiers return input unchanged.
- **Layout & snapping** — `align-parent-axis-projection`: parent-space wrapper + delta-as-axis-vector projection; `calc-align-pos` is the pure six-case core.
- **Layout & snapping** — `distribute-space-unit-interval`: center-sort, unit = free/(n−1), forward loop; gaps equalized between wrapping rects, not centers.
- **Layout & snapping** — `viewport-fit-min-zoom-floor`: fit-then-floor; the floor branch re-centers a viewport/min-zoom box on the ORIGINAL corner, discarding padding.
- **Bounds propagation** — `bounds-map-delay-volatile-propagation`: delays over a late-vreset! volatile give groups NEW child geometry lazily; old-entry ref breaks self-reference.
- **Bounds propagation** — `create-bounds-mask-single-child`: mask=1 child, group=children∪self-modified, leaf=self; `ctm/empty?` gate; width/height clamp ≥0.01.
- **Layout & snapping** — `grid-generic-algebra`: `[size item-length next-v gutter]` tuple with ordered size/item-length derivation and per-type offset/stretch ladders.
- **Layout & snapping** — `snap-point-vocabulary`: set-based candidate tiers (rect⊂frame), tri-conditional guide suppression w/ rotated-frame hatch, display+axis-gated grid lines.
- **Constraint propagation** — `constraints-vocabulary-defaults`: 8→4 reduction table + computed tree-position defaults (root→nil, frame-child→:left/:top, group-child→:scale).
- **Constraint propagation** — `constraint-anchor-line-intersection`: anchors = child-corner ray ∥ parent edge ∩ opposite side, all inside parent space.
- **Constraint propagation** — `constraint-displacement-sign-algebra`: keep before-length, take after-direction; unsigned-angle before/after comparison is the flip witness.
- **Constraint propagation** — `fixed-constraint-resize-sandwich`: normalize (child frame) THEN :fixed resize (parent frame) + disp-start move; double 0.01 clamps.
- **Constraint propagation** — `calc-child-constraint-gates`: five ordered exits; transformed-parent-bounds delay deref'd only on the full path.
- **Constraint propagation** — `wasm-constraint-twin-axis-aligned`: Rust AABB twin — pass-through/scale/displace; rotated-parent fidelity is editor-only.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
penpot (MPL-2.0), `develop@64a52d6b` (pass 2 fast-forwarded the pass-1 pin dd6b521b by +6 upstream commits; pass 3 re-entered at UNCHANGED pin; pass 4 re-entered at the SAME HEAD `develop@64a52d6b04328cf2d4d388bba7876e017d594aa8`; pass 5 re-entered at the SAME HEAD — no drift since pass 3); Codebase Memory project `penpot` (PASS-4 TWIN MIGRATION: the prior graph projects `ext-penpot` and its fresh twin `mnt-hdd-utopia-inspo-external-penpot` were DELETED from the shared store; pass 4 registered the short-name project `penpot` via full-mode re-index — 44,547 nodes / 162,456 edges, generation 2026-08-25T20:11:45Z, head==base 64a52d6b; pass 5 verified the same generation/counts live via index_status). parse_partial confined to SQL templates/migrations + SCSS + nginx/tmux/pg_hba configs, none cited in any capsule. New pass-4/pass-5 capsules cite project `penpot`; the 30 earlier capsules retain their historical `mnt-hdd-utopia-inspo-external-penpot` citations, which are byte-equal at this identical HEAD but must be re-pointed if that HEAD ever moves).

## Full view (memory graph)
Revalidate `penpot` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Pass-4 evidence @ 64a52d6b: check_index_coverage ×8 (align/grid/snap/bounds_map sources + geom_align/geom_snap/geom_grid/geom_bounds_map tests) all no_recorded_issue + metadata_match + generation_matches=true @ generation 2026-08-25T20:11:45Z. Pass-4 retrieval liveness: 7/7 capsule Retrieve queries live-resolved rank#1 (or rank#1–#5 with named hits) on project `penpot` — align/distribute/viewport/bounds-map/create-bounds/grid/snap queries all returned line-exact matches matching the cited ranges. Graph caveat: inbound trace_path CALLS edges are unresolved for the pass-4 Clojure seams (callers_total=0 for transform-bounds-map, grid-snap-points, distribute-space); consumers confirmed from source instead (modifiers.cljc :81/:120/:306/:356-381; frontend main.snap.cljs get-snap-points). Pass-5 evidence @ 64a52d6b: check_index_coverage ×5 cited paths (constraints.cljc, modifiers.cljc, geom_shapes_constraints_test.cljc, render-wasm constraints.rs, shapes/transforms.cljc) all no_recorded_issue + metadata_match + generation_matches=true. Pass-5 retrieval liveness: 6/6 capsule Retrieve queries live-resolved with the cited symbols at the cited ranges (vocabulary rank#1/#2/#4; anchor vectors rank#1–#4; displacement rank#1/#2; fixed/normalize rank#1 + named#2 of 536; gates rank#1 of 1120 with consumer names; wasm twin rank#1–#3 of 1489). Standing caveat: trace_path inbound callers_total=0 for calc-child-modifiers — consumer chain proven from modifiers.cljc :36–65/:137–151/:190–194/:368 source reads. Direct-test honesty: geom_shapes_constraints_test.cljc is 27 lines pinning ONLY the :default multimethod arity fix; every other constraint claim is source-only evidence.

## Boundaries
Adopt the pure common-library contracts (change ledgers, op-log transforms, lazy maps, undo stack, file-migration ledger, traversal protocol, the pass-3 geometry/transform kernel: affine recovery, move-vs-generic dispatch, four-bucket op log, group/mask regeneration, modif-tree persistence, precision guards, row-vector/center conventions, matrix pair, convenience builders, entry funnel, the pass-4 layout plane: parent-axis alignment projection, unit-interval distribution, viewport fit floor, delay/volatile bounds propagation, mask-single-child bounds rule, grid algebra, snap vocabulary, and the pass-5 constraint-propagation plane: vocabulary reduction + tree-derived defaults, frame-local anchor intersections, displacement sign algebra, fixed-constraint resize sandwich with deformation pre-strip, five-exit gating ladder with lazy parent-bounds deref, and the wasm AABB twin parity boundary); adapt host-specific serialization (fressian/transit tags, Malli schema hooks), the JVM/JS reader-conditional split, and the backend/session/error surfaces to your stack; omit penpot product surfaces (workspace UI beyond the stats seam, exporter, render-wasm Rust twin of modifiers EXCEPT its constraints.rs module mined in pass 5, media-processor, MCP server), svg.cljc export serialization (queued on an SVG-porting question), flex/grid LAYOUT ENGINES (shapes/flex_layout/* and shapes/grid_layout/* — auto-layout child placement is its own plane, distinct from the pass-4 top-level grid/snap helpers AND from the pass-5 constraint gates that early-return to it), pixel_precision.cljc (cited only as a consumer hook), and types/path/* (segment/helpers/bool/shape_to_path ~3.7k LOC with its own 1,594L test suite — its own deep plane).
