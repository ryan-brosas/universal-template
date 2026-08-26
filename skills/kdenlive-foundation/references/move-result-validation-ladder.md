<!-- capsule-v2 -->
# Move validation ladder — which checks run before a clip is allowed to move, and what does each failure mean?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive`. **Question:** A porter must decide the exact order and granularity of rejection reasons for a timeline move so the UI can explain WHY a drop failed, while guaranteeing a failed move leaves zero state behind.

## Typed MoveResult taxonomy + compensating rollback
**Path/Symbol:** `src/timeline2/model/timelinemodel.hpp:MoveResult` (184), `src/timeline2/model/timelinemodel.cpp:TimelineModel::requestClipMove` (837–1097, functor overload; public wrapper 1419–1453).
**Signature:** `MoveResult requestClipMove(int clipId, int trackId, int position, bool moveMirrorTracks, bool updateView, bool invalidateTimeline, bool finalMove, Fun &undo, Fun &redo, bool revertMove, bool groupMove, const QMap<int,int> &moving_clips, std::pair<MixInfo,MixInfo> mixData)`.
**Data Shape:** `enum MoveResult { MoveSuccess, MoveErrorAudio, MoveErrorVideo, MoveErrorType, MoveErrorOther }`. Inputs: clip id, target trackId/position; `finalMove` distinguishes drag-preview from commit; `revertMove` marks undo-driven repositions that skip availability checks; `moving_clips` lists co-moving group members.

### Decisive source
```cpp
if (m_allClips[clipId]->clipState() == PlaylistState::Disabled) {
    if (getTrackById_const(trackId)->trackType() == PlaylistState::AudioOnly && !m_allClips[clipId]->canBeAudio())
        return MoveErrorAudio;
    if (getTrackById_const(trackId)->trackType() == PlaylistState::VideoOnly && !m_allClips[clipId]->canBeVideo())
        return MoveErrorVideo;
} else if (getTrackById_const(trackId)->trackType() != m_allClips[clipId]->clipState()) {
    return MoveErrorType;                                   // audio / video mismatch
}
...
if (m_editMode == TimelineMode::NormalEdit && !getTrackById_const(trackId)->isAvailableWithExceptions(position, getClipPlaytime(clipId), exceptions)) {
    return MoveErrorOther;                                  // no free space
}
...
ok = ok && getTrackById(trackId)->requestClipInsertion(clipId, position, ...);
if (!ok) {
    bool undone = local_undo();
    Q_ASSERT(undone);
    return MoveErrorOther;
}
```

**Flow:** short-circuit no-op if position+track unchanged → type/state ladder (Disabled clips probe capability; active clips require exact state match) → same-track moves degrade to view-only notify (`update_model` functor) → start-mix/end-mix boundary guards abort with Other when the move would cross a mix whose partner isn't co-moving → availability check with exceptions `{clipId, mix partners}` ONLY in NormalEdit AND only when `!finalMove && !revertMove` → mutation = old-track deletion then new-track insertion → any failure runs accumulated `local_undo()` and asserts it held.
**Invariant:** A rejected move mutates nothing observable; an accepted preview (`!finalMove`) may place fake positions (`setFakeTrackId/setFakePosition` in non-NormalEdit modes) but never commits until finalMove; rollback itself must succeed or the process asserts.
**Probe:** `tests/modeltest.cpp` "Undo and Redo" suite (:1309+) drives `requestClipMove` across tracks with per-step `checkConsistency()` and undo round-trips; `tests/trimmingtest.cpp:146-150` pins resize-side failure codes returning -1 on impossible growth.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "kdenlive", query: "requestClipMove validate request functor undo", limit: 40 });
// executed live (name_pattern ^request.*): requestClipMove timelinemodel.cpp:1419-1453 (public),
// TrackModel::requestClipInsertion_lambda :176-303, requestClipCut timelinefunctions.cpp:258-364
```

## Verdict
Adopt the typed-failure ladder order (type gates before collision checks) and delete-then-insert as the universal move implementation. Adapt MoveResult to your host's error enum; keep "preview skips availability, commit re-validates" — dropping it breaks drag UX. Omit MLT playlist internals and QML notify roles; replace them with your model's own change notifications.
