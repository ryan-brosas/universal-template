---
name: kdenlive-foundation
description: "Use when porting kdenlive timeline document-model machinery — Fun undo-lambda composition on QUndoStack, typed move-validation with rollback, two-phase group moves on an upLink/downLink forest, functor clip insertion into MLT playlists, refcounted snap grids with speed-remapped projection, snap-aware resize trials, group-scoped cuts with predicate tree splits, same-track mix plant/replant ladders, speed unplant/swap/replant kernels, spacer ripples with temporary ungroup, selection-as-group-node with track locks, time-remap rebuilds, mix load recovery, zone extract/lift/insert/overwrite as single-undo ops, subtitle events on the group/snap/lock planes, and paste id-remapping with post-insert group/mix reconstruction."
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
- `references/clip-cut-group-split-dance.md` — splitting one clip at a frame across its whole group scope: clone/resize/move per clip, then root-only group-tree split by position criterion.
- `references/mix-plant-replant-ladder.md` — same-track crossfade creation: delete → replant → build_mix → resize ladder with mirrored destroy_mix reverse and chained-mix playlist rearrangement.
- `references/mix-info-sync-plane.md` — derive-don't-store mix geometry: live MixInfo derivation, post-mutation syncronizeMixes reconciliation with drag-stub vs commit-delete collapse.
- `references/timewarp-unplant-replant-kernel.md` — speed change as unplant → producer swap → replant, with sign-flip in/out re-anchoring, one-frame floor, and the resize-and-warp composite.
- `references/spacer-ripple-ungroup-regroup-dance.md` — insert/remove space across tracks: start/end pair with module-static operation state, temporary ungroup/regroup of boundary leaves, transient snap point, one-primitive commit.
- `references/selection-group-lock-plane.md` — selection as a GroupType::Selection node in the same forest (created without undo) plus the undoable track-lock gate on every mutation entry point.
- `references/timeremap-enable-disable-kernel.md` — per-frame speed map as unplant → bin-rebuild → replant with curve capture-before/re-apply-after and input-duration restore on disable.
- `references/mix-persistence-loadmix-recovery.md` — mixes surviving copy/paste (id correspondence table) and project load (position-derived clip recovery with swap retry and impossible-order disconnect).
- `references/zone-extract-lift-kernel.md` — delete/collapse a frame range across tracks as one undo entry: break affected groups first, mix-aware edge cuts (inside-mix ⇒ delete whole), then one representative move ripples the rest.
- `references/zone-insert-overwrite-ripple.md` — open or replace a frame range: shared target-election prelude, overwrite = lift-all vs insert = cut + positive-delta ripple on private accumulators folded only on success.
- `references/subtitle-event-model-plane.md` — subtitles as (layer,start)-keyed events rendered by an MLT filter side file, yet inside the same id space, snap grid, lock gates, group forest, and fake-position projection as clips.
- `references/paste-id-remapping-plane.md` — copy/paste as one semaphore-guarded transaction: position-based clipboard, tracksMap lane election with audio mirrors, bin-id remapping for cross-document paste, correspondingIds table, then post-insertion mix/composition/subtitle/group reconstruction.

## Capsule map
- **Undo functor kernel** — `fun-undo-composition-kernel`: `Fun = std::function<bool(void)>`; UPDATE_UNDO_REDO prepends reverse to undo / appends operation to redo; FunctionalUndoCommand's m_undone latch prevents QUndoStack push-time double redo; DocUndoStack::push emits invalidate(index()) when truncating.
- **Move validation ladder** — `move-result-validation-ladder`: MoveResult taxonomy {Success, ErrorAudio, ErrorVideo, ErrorType, Other}; type/state gates, mix boundary guards, availability check only in NormalEdit && !finalMove; mutation is delete+insert; failure runs local_undo() then asserts.
- **Group two-phase move** — `group-move-two-phase`: sort by move direction, snapshot mixes-to-delete first, clamp delta_track to 0 on A/V mirror violations, remove-all then reinsert so intra-group items never collide.
- **Track insertion ownership** — `track-insertion-ownership-ladder`: capture inverse BEFORE construct; redo lambda holds shared_ptr keeping the track alive on the stack; compositions retargeted; ids from one monotonic KdenliveDoc::next_id.
- **Insertion functor ladder** — `clip-insertion-functor-ladder`: validator returns append / fit-in-blank / always-false functor; MLT field+playlist lock sandwich; end_function registers clip, snaps both edges, beginInsertRows.
- **Groups forest** — `groups-forest-updown-links`: upLink/downLink maps cover every id; getRootId walks UP with cycle detection; setGroup auto-promotes Leaf→Normal; groupItems returns existing root instead of creating singleton groups.
- **Snap plane** — `snap-refcount-projection`: std::map<int,int> refcounts; ignore/unIgnore withdraws own edges; ClipSnapModel projects source-frame markers through speed (`pos/speed`, ceil, reversed formula for negative speed) via weak_ptr registration.
- **Resize proposal** — `resize-snap-trial-proposal`: addPoint(playhead)→proposeSize→removePoint; trial resize rolled back with temp_undo; TrackModel decision tree answers shrink/grow-right/grow-left with blank-capacity arithmetic or false sentinels.
- **Clip cut + group split** — `clip-cut-group-split-dance`: clearSelection FIRST (selection groups have no undo); per clip clone→resize→(reassign end mix)→move with ONE shared accumulator; clones join the group BEFORE GroupsModel::split(root, pos<criterion) BFS-copies the subtree with temp negative ids, prunes empty groups, rebuilds bottom-up preserving GroupType.
- **Mix plant/replant ladder** — `mix-plant-replant-ladder`: two sub-playlists per track; delete second clip → setSubPlaylistIndex → rearrange_playlists (blank/move/replug chained partners + updateCompositionDirection) → reinsert → build_mix (plant transition, kdenlive:mixcut, reversed tracks when dest_track==0) → resize both clips to the overlap; reverse = destroy_mix + mirrored ladder; paired registries m_mixList(first→second)/m_sameCompositions(second→asset) always change together.
- **Mix info/sync plane** — `mix-info-sync-plane`: MixInfo fully derived at read time from registries + live positions (-1 sentinel for deleted partner); syncronizeMixes(finalMove) reconciliation after every move/resize family: orphan mixes disconnected+deleted, windows recomputed from positions, non-positive overlap = 1-frame stub mid-drag vs zero+delete on commit.
- **Timewarp unplant/replant** — `timewarp-unplant-replant-kernel`: producer swap only takes effect on unplant/replant (delete→useTimewarpProducer→insert at oldPos); newDuration=qMax(1, round(d·|prev/speed|)); sign flip re-anchors in/out at source end; reverse restores oldIn/oldOut on shrinking swaps; resize-and-warp composite scales selection by speed ratio, split partner only when edge-aligned, typed three-way failure messages.
- **Spacer ripple** — `spacer-ripple-ungroup-regroup-dance`: start/end pair over module-statics (spacerUngroupedItems leaf→parent parking map, spacerMin/MaxPosition); start clears selection, parks out-of-range group leaves, clamps space by relatedMaxSpace, adds a TRANSIENT snap point; end removes it, restores the anchor, optionally liftZone in OverwriteEdit, commits EXACTLY ONE requestGroupMove/requestClipMove, regroups parked leaves only on success; delete-blank refuses same-group flanks; delete-all-blanks folds per-blank undos into one stack entry.
- **Selection & lock plane** — `selection-group-lock-plane`: m_currentSelection holds one GroupType::Selection node or a flat id set; multi-root selection calls groupItems with THROWAWAY accumulators (selection never reaches the undo stack), clear destructs the node, getCurrentSelection is the single leaf-expansion point, requestClipsGroup refuses Selection type; locks are an undoable Lock-track command + entry-point trackIsLocked guards with a bypassLock escape for internal replants.
- **Time remap kernel** — `timeremap-enable-disable-kernel`: enable/disable = unplant → refreshProducerFromBin(enableRemap) → replant at oldPos; timeremap link's time_map/pitch/image_mode captured BEFORE the bin rebuild and re-applied AFTER; disable restores visible duration parsed from the map string (max − value-at-in) via requestItemResize; split partner processed first in one shared accumulator; resize max-duration guards exempt remapped clips.
- **Mix persistence** — `mix-persistence-loadmix-recovery`: three createMix overloads share the paired-registry tail; mixXml serializes ids+live geometry+params into <mix>; paste remaps ids through a correspondence table and scales by ratio; loadMix re-derives the clip pair from positions (reverse-aware sub-playlist index, swapped-index retry, SWAPPING-CLIPS heuristic, impossible-order disconnect under field lock) and resyncs transition in/out to live clip positions.
- **Zone extract/lift** — `zone-extract-lift-kernel`: breakAffectedGroups ungroups only out-of-range leaves; liftZone cuts both edges mix-aware (cut pos inside the mix overlap ⇒ ungroup+delete whole); locked tracks skipped not failed; extract appends removeSpace = ONE representative move of everything from zone end to ∞ through the ordinary move ladders; caller regroups parked leaves success-only; whole op = one undo entry.
- **Zone insert/overwrite** — `zone-insert-overwrite-ripple`: explicit-minus-locked vs target-flag lane election; overwrite = liftZone per track, insert = cut boundary clip + requestInsertSpace (positive-delta mirror of removeSpace) on PRIVATE local_undo/local_redo rolled back+asserted on failure and folded via UPDATE_UNDO_REDO_NOLOCK only on success; optional mid-op audio-track prompt retroactively joins affectedTracks.
- **Subtitle event model** — `subtitle-event-model-plane`: std::map<(layer,GenTime),SubtitleEvent> + id index, no playlist entries; validation ladder (locked/negative/inverted/duplicate-slot/layer-bounds) at every entry point; razor-mode cut = resize original + new-id sibling (no line break ⇒ refused); left resize = erase+reinsert (start is in the key); both edges feed the shared snap grid; locked subtitle aborts group moves; filter JSON side file rewritten lazily via first/last flags.
- **Paste id remapping** — `paste-id-remapping-plane`: <kdenlive-scene> clipboard carries offset/masterTrack-position/fps-ratio, never absolute ids; QSemaphore(1) module static guards the transaction; findPerfectTracks preserves above/below lane counts; useFreeBinId+mappedIds resolve cross-document bin collisions; correspondingIds[old→new] filled during re-insertion; mixes/compositions/subtitles/groups reconstructed strictly AFTER all clips exist (fromJsonWithOffset applies id table + tracksMap); unselect lambda prepended to both undo and redo.

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
