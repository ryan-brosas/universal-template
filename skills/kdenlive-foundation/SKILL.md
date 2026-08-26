---
name: kdenlive-foundation
description: Use when porting kdenlive's timeline document-model machinery — Fun undo-lambda composition over QUndoStack, typed move-validation ladders with compensating rollback, two-phase group moves across an upLink/downLink forest, validation-by-functor clip insertion into MLT playlists, refcounted snap grids with per-clip speed-remapped projection, and snap-aware trial resize proposals.
---

# kdenlive: timeline document-model foundation

## Use this for
Use when porting frame-accurate timeline/document-model internals from kdenlive: undo-safe mutation
kernels, group-hierarchy propagation, collision/mix-boundary validation, MLT playlist bookkeeping,
snap-grid aggregation, and trim/resize state machines. Source code and direct tests are ground truth;
references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/fun-undo-composition-kernel.md` — how every model op becomes composed `Fun` lambdas on a DocUndoStack without double-execution.
- `references/move-result-validation-ladder.md` — which checks run before a clip moves, and what each failure code means.
- `references/group-move-two-phase.md` — moving a whole group without self-collisions (remove-all, then reinsert).
- `references/track-insertion-ownership-ladder.md` — eager construct + captured-shared_ptr undo ownership; one global id counter.
- `references/clip-insertion-functor-ladder.md` — validators that return functors (or an always-false sentinel) instead of booleans.
- `references/groups-forest-updown-links.md` — the item-group forest: root walk, relinking, auto-promotion, single-root short-circuit.
- `references/snap-refcount-projection.md` — refcounted snap points plus per-clip marker projection with speed remapping.
- `references/resize-snap-trial-proposal.md` — snapping a requested size via transient playhead point + trial resize + rollback.

## Capsule map
- **Undo functor kernel** — `fun-undo-composition-kernel`: `Fun = std::function<bool(void)>`; UPDATE_UNDO_REDO prepends reverse to undo / appends operation to redo; FunctionalUndoCommand's m_undone latch prevents QUndoStack push-time double redo; DocUndoStack::push emits invalidate(index()) when truncating.
- **Move validation ladder** — `move-result-validation-ladder`: MoveResult taxonomy {Success, ErrorAudio, ErrorVideo, ErrorType, Other}; type/state gates, mix boundary guards, availability check only in NormalEdit && !finalMove; mutation is delete+insert; failure runs local_undo() then asserts.
- **Group two-phase move** — `group-move-two-phase`: sort by move direction, snapshot mixes-to-delete first, clamp delta_track to 0 on A/V mirror violations, remove-all then reinsert so intra-group items never collide.
- **Track insertion ownership** — `track-insertion-ownership-ladder`: capture inverse BEFORE construct; redo lambda holds shared_ptr keeping the track alive on the stack; compositions retargeted; ids from one monotonic KdenliveDoc::next_id.
- **Insertion functor ladder** — `clip-insertion-functor-ladder`: validator returns append / fit-in-blank / always-false functor; MLT field+playlist lock sandwich; end_function registers clip, snaps both edges, beginInsertRows.
- **Groups forest** — `groups-forest-updown-links`: upLink/downLink maps cover every id; getRootId walks UP with cycle detection; setGroup auto-promotes Leaf→Normal; groupItems returns existing root instead of creating singleton groups.
- **Snap plane** — `snap-refcount-projection`: std::map<int,int> refcounts; ignore/unIgnore withdraws own edges; ClipSnapModel projects source-frame markers through speed (`pos/speed`, ceil, reversed formula for negative speed) via weak_ptr registration.
- **Resize proposal** — `resize-snap-trial-proposal`: addPoint(playhead)→proposeSize→removePoint; trial resize rolled back with temp_undo; TrackModel decision tree answers shrink/grow-right/grow-left with blank-capacity arithmetic or false sentinels.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add
one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
kdenlive (GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL; COPYING = GPLv3), `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`;
Codebase Memory project `kdenlive` (full index 2026-08-26T01:41:22Z, 25,325 nodes / 102,285 edges;
skipped=0; parse_partial=468 mostly po/*.po + vendored catch/fakeit headers — cited src/test paths
coverage-checked individually, flagged single lines read directly).

## Full view (memory graph)
Revalidate `kdenlive` before porting: run `index_status`, `check_index_coverage`, `search_graph`,
`trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts,
freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure model contracts: Fun composition + rollback discipline, validation-before-mutation,
group forest algebra, refcounted snap grid, id unicity. Adapt Qt signal/dataChanged emission, MLT
playlist calls, and KdenliveSettings hooks to your host's storage/renderer equivalents. Omit the QML
view layer, KDE i18n/i18n plumbing, render job scheduling, and app-level monitor logic.
