<!-- capsule-v2 -->
# Clip-cut mix/fade interior — how do you cut ONE clip at a frame when it carries mix endpoints and fade effects, so the clone lands on the right sub-playlist with the mix moved and the fades split honestly?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter must split a clip that may carry an end mix (same-track transition), a start mix, and fade in/out effects; the left half must keep its identity, the right half is a fresh clone, and the mix registration, sub-playlist placement, and fade effects must all end up on the correct side — atomically, on the caller's undo accumulators.

## processClipCut: clone → resize → reassign end mix → playlist switch → fade cleanup → move
**Path/Symbol:** `src/timeline2/model/timelinefunctions.cpp:TimelineFunctions::processClipCut` (150–237), `cloneClip` (80–112); `src/effects/effectstack/model/effectstackmodel.cpp:EffectStackModel::cleanFadeEffects` (1845–1878); `src/timeline2/model/trackmodel.cpp:TrackModel::reAssignEndMix` (2750–2758), `switchPlaylist` (156–175); `src/timeline2/model/clipmodel.cpp:ClipModel::passTimelineProperties` (1346–1352).
**Signature:** `bool processClipCut(const std::shared_ptr<TimelineItemModel> &timeline, int clipId, int position, int &newId, Fun &undo, Fun &redo)`; `bool cloneClip(const std::shared_ptr<TimelineItemModel> &timeline, int clipId, int &newId, PlaylistState::ClipState state, int audioStream, Fun &undo, Fun &redo)`.
**Data Shape:** operates on the caller's shared `Fun &undo/Fun &redo` accumulators (no local pair — the caller owns rollback); `newId` is the clone's id; reads `hasEndMix/hasStartMix` from the track, `subplaylist` = `m_allClips[clipId]->getSubPlaylistIndex()`, `state` = `clipState()`; `m_blockRefresh` is set true for the whole interior and false on exit.

### Decisive source
```cpp
// timelinefunctions.cpp:170-237 — the interior's exact stage order IS the contract
bool res = cloneClip(timeline, clipId, newId, state, -1, undo, redo);   // 1. clone (fresh producer)
...
int updatedDuration = position - start;
res = timeline->m_allClips[clipId]->requestResize(updatedDuration, true, undo, redo, true, hasEndMix || hasStartMix);  // 2. shrink original

if (hasEndMix) {
    // Assign end mix to new clone clip
    Fun local_redo = [timeline, trackId, clipId, newId]() { return timeline->getTrackById_const(trackId)->reAssignEndMix(clipId, newId); };
    local_redo();
    PUSH_LAMBDA(local_redo, redo);
    Fun local_undo = [timeline, trackId, clipId, newId]() {
        timeline->getTrackById_const(trackId)->reAssignEndMix(newId, clipId);   // 3. mix follows the RIGHT half
        return true;
    };
    PUSH_LAMBDA(local_undo, undo);
    if (!hasStartMix && subplaylist != 0) {
        // If the clip has no start mix, move to playlist 0
        Fun local_redo2 = [timeline, trackId, clipId, start]() {
            return timeline->getTrackById_const(trackId)->switchPlaylist(clipId, start, 1, 0);
        };
        ...
    }
}
...
if (res) {
    std::shared_ptr<EffectStackModel> sourceStack = timeline->getClipEffectStackModel(clipId);
    sourceStack->cleanFadeEffects(true, undo, redo);    // 4. original loses its fade OUTS
    std::shared_ptr<EffectStackModel> destStack = timeline->getClipEffectStackModel(newId);
    destStack->cleanFadeEffects(false, undo, redo);     //    clone loses its fade INS
}
updatedDuration = duration - newDuration;
res = res && timeline->requestItemResize(newId, updatedDuration, false, true, undo, redo);   // 5. shrink clone
...
res = res && (timeline->requestClipMove(newId, trackId, position, true, true, false, true, undo, redo) == TimelineModel::MoveSuccess);  // 6. place clone
```
```cpp
// effectstackmodel.cpp:1845-1878 — fade cleanup is itself undoable, on the caller's accumulators
const auto &toDelete = outEffects ? m_fadeOuts : m_fadeIns;
for (int id : toDelete) {
    auto effect = std::static_pointer_cast<EffectItemModel>(getItemById(id));
    Fun operation = removeItem_lambda(id);
    if (operation()) {
        Fun reverse = addItem_lambda(effect, rootItem->getId());
        UPDATE_UNDO_REDO(operation, reverse, undo, redo);
    }
}
if (!toDelete.empty()) { /* updateRedo: erase from m_fadeIns/m_fadeOuts sets + customDataChanged + PUSH_LAMBDA */ }
```
```cpp
// clipmodel.cpp:1346-1352 — what a clone actually inherits (deliberately tiny)
void ClipModel::passTimelineProperties(const std::shared_ptr<ClipModel> &other) {
    Mlt::Properties source(m_producer->get_properties());
    Mlt::Properties dest(other->service()->get_properties());
    dest.pass_list(source, "kdenlive:hide_keyframes,kdenlive:activeeffect");
}
```

**Flow:** (1) `cloneClip` creates a fresh clip from the same bin id (capturing speed, warp_pitch, audio_index), copies `m_endlessResize` and the two timeline properties via `passTimelineProperties`, imports ALL effects, and double-resizes when the source's playtime differs from the fresh producer length; (2) the ORIGINAL is shrunk to `position - start` (with `hasEndMix || hasStartMix` telling the resize ladder to tolerate the mix boundary); (3) if the original had an END mix, the mix registration is MOVED to the clone via `reAssignEndMix` (the `m_mixList` entry is re-keyed currentId→newId) — the transition now belongs to the right half; if the clip had no START mix and sat on sub-playlist 1, the original is switched back to playlist 0 (`switchPlaylist(clipId, start, 1, 0)`) so the freed second playlist is clean; (4) fade effects are split honestly: the original's fade-OUTS and the clone's fade-INS are removed through `cleanFadeEffects`, each removal an undoable operation on the shared accumulators; (5) the clone is resized to `duration - newDuration` and moved to `position` on the same track; (6) if the track duration changed during all this, an `updateDuration` lambda is pushed onto redo. The whole interior runs with `m_blockRefresh = true` so no intermediate view refresh fires.
**Invariant:** the mix endpoint travels with the RIGHT half (clone), never stays with the original; the original's playlist index is restored to 0 unless it also has a start mix (chained mixes keep both halves on their playlists — pinned by mixtest); every mutation stage appends to the CALLER's accumulators, so a failure anywhere lets the caller roll back the entire cut, not just this clip; fades are removed, never re-timed — a fade crossing the cut point is dropped, not split.
**Probe:** `tests/mixtest.cpp:174-205` "Create mix and cut on color clips": cutting a mix-end clip at 505 leaves original AND clone on playlist 0 (`getClipSubPlaylistIndex == 0` for both); cutting a mix-start clip at 535 leaves the original on playlist 1 and the clone on playlist 0; undo restores the pre-cut state. `tests/modeltest.cpp:1236-1252` "Clip clone": `cloneClip` succeeds and the clone shares the bin id. `tests/trimmingtest.cpp:60-92` "Trivial split": cuts outside the clip and ON the edges return TRUE and change nothing (empty-cut contract).

## Get live surrounding code
**Retrieve:**
```bash
$ grep -n 'processClipCut\|cloneClip' src/timeline2/model/timelinefunctions.cpp
80:bool TimelineFunctions::cloneClip(const std::shared_ptr<TimelineItemModel> &timeline, int clipId, int &newId, PlaylistState::ClipState state, int audioStream,
150:bool TimelineFunctions::processClipCut(const std::shared_ptr<TimelineItemModel> &timeline, int clipId, int position, int &newId, Fun &undo, Fun &redo)
170:    bool res = cloneClip(timeline, clipId, newId, state, -1, undo, redo);
332:        bool res = processClipCut(timeline, cid, position, newId, undo, redo);
1087:            res = cloneClip(timeline, id, newId, state, -1, undo, redo);
1246:            bool res = cloneClip(timeline, cid, newId, PlaylistState::AudioOnly, stream, undo, redo);
1309:            bool res = cloneClip(timeline, cid, newId, PlaylistState::VideoOnly, -1, undo, redo);
$ grep -n 'cleanFadeEffects' src/effects/effectstack/model/effectstackmodel.cpp
1845:void EffectStackModel::cleanFadeEffects(bool outEffects, Fun &undo, Fun &redo)
# executed live this pass; graph search_graph unavailable (MCP not connected in session)
```

## Verdict
Adopt the stage order verbatim: clone → shrink original → move mix registration to the right half → playlist hygiene → fade cleanup (outs from left, ins from right) → shrink clone → place clone. Adopt "fades are dropped, not re-timed" — re-timing a fade across a split needs keyframe math kdenlive deliberately avoids here. Adopt the caller-owned accumulators so a per-clip failure rolls back the whole multi-clip cut. Adapt `cleanFadeEffects` to your host's effect model (the reusable shape is: id-set of boundary effects, remove-with-undo, then one view-update lambda pushed to redo). Omit `m_blockRefresh` if your host has no batched view refresh. Porting risk: the subtitle cut path (`cutSubtitle`) has NO test in the repo — add a fixture before relying on it.
