<!-- capsule-v2 -->
# Zone insert/overwrite ripple — how do you insert or overwrite a frame range across tracks as one undoable operation: cut boundary clips, ripple everything after it right by exactly the zone width, then plant the new clip?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter needs "insert zone" (open a hole of N frames at frame F across the target tracks and drop a clip in) and "overwrite zone" (replace whatever is in [F, F+N) with the new clip) — both as single undo entries, reusing the same validated move ladders as every other mutation.

## insertZone target selection + overwrite-lift vs cut-and-ripple + requestInsertSpace single-move mirror
**Path/Symbol:** `src/timeline2/model/timelinefunctions.cpp:TimelineFunctions::insertZone` public (811–824) and core (826–909), `requestInsertSpace` (1026–1073); module statics `waitingBinIds`/`mappedIds`/`sequencesToInit`/`tracksMap` + `QSemaphore semaphore(1)` at :70–77 (shared with the paste plane, see paste-id-remapping-plane).
**Signature:** `static bool insertZone(const std::shared_ptr<TimelineItemModel> &timeline, QList<int> trackIds, const QString &binId, int insertFrame, QPoint zone, bool overwrite, bool useTargets, Fun &undo, Fun &redo)`; `static bool requestInsertSpace(const std::shared_ptr<TimelineItemModel> &timeline, QPoint zone, Fun &undo, Fun &redo, const QVector<int> &allowedTracks)`.
**Data Shape:** `QPoint(insertFrame, insertFrame + zoneWidth)`; `useTargets=true` means "all tracks whose target flag is set" (`shouldReceiveTimelineOp()`), otherwise the explicit `trackIds` list minus locked tracks.

### Decisive source
```cpp
// timelinefunctions.cpp:826-877 — affected-track election, then two mutually exclusive strategies
if (!useTargets) {
    for (int target_track : trackIds) {
        if (!timeline->getTrackById_const(target_track)->isLocked()) {
            affectedTracks << target_track;
        }
    }
} else {
    while (it != timeline->m_allTracks.cend()) {
        if (timeline->getTrackById_const(target_track)->shouldReceiveTimelineOp()) {
            affectedTracks << target_track;
        } else if (trackIds.contains(target_track)) {
            trackIds.removeAll(target_track);        // marked target but inactive → drop from insertion list too
        }
        ++it;
    }
}
...
result = breakAffectedGroups(timeline, affectedTracks, QPoint(insertFrame, insertFrame + (zone.y() - zone.x())), undo, redo);
if (overwrite) {
    for (int target_track : std::as_const(affectedTracks)) {
        result = result && TimelineFunctions::liftZone(timeline, target_track, QPoint(insertFrame, insertFrame + (zone.y() - zone.x())), undo, redo);
        if (!result) { break; }                       // overwrite = liftZone on EVERY affected track
    }
} else {
    for (int target_track : std::as_const(affectedTracks)) {
        int startClipId = timeline->getClipByPosition(target_track, insertFrame);
        if (startClipId > -1) {
            result = result && TimelineFunctions::requestClipCut(timeline, startClipId, insertFrame, undo, redo);  // cut the boundary clip
        }
    }
    result = result && TimelineFunctions::requestInsertSpace(timeline, QPoint(insertFrame, insertFrame + (zone.y() - zone.x())), undo, redo, affectedTracks);
}
```
```cpp
// timelinefunctions.cpp:878-905 — after the hole exists, plant the new clip (with optional audio-stream prompt)
QString binClipId = QStringLiteral("%1/%2/%3").arg(binId).arg(zone.x()).arg(zone.y() - 1);   // binId/in/out
if (!useTargets) {
    const QList<int> audioTracksBefore = timeline->getTracksIds(true);
    QVariantList streamInfo = timeline->clipAudioStreamInfo(binClipId, trackIds.first(), true, undo, redo);
    if (streamInfo[0].toInt() == -1) { return false; }   // user cancelled track creation
    const QList<int> audioTracksAfter = timeline->getTracksIds(true);
    for (int tid : audioTracksAfter) {
        if (!audioTracksBefore.contains(tid) && !affectedTracks.contains(tid)) {
            affectedTracks << tid;                        // freshly prompted audio tracks join the op
        }
    }
}
result = timeline->requestClipInsertion(binClipId, trackIds.first(), insertFrame, newId, true, true, useTargets, undo, redo, affectedTracks);
```
```cpp
// timelinefunctions.cpp:1026-1073 — requestInsertSpace: MIRROR of removeSpace, positive delta
timeline->requestClearSelection();
Fun local_undo = []() { return true; };
Fun local_redo = []() { return true; };
for (auto target_track : allowedTracks) {
    std::unordered_set<int> subs = timeline->getItemsInRange(target_track, zone.x(), -1, true);   // from zone start to ∞
    items.insert(subs.begin(), subs.end());
}
if (items.empty()) { return true; }                        // nothing to move = success, no-op
timeline->requestSetSelection(items);
int targetPos = timeline->getItemPosition(itemId) + zone.y() - zone.x();   // positive delta = right
if (timeline->m_groups->isInGroup(itemId)) {
    result = result && timeline->requestGroupMove(itemId, ..., 0, zone.y() - zone.x(), true, true, local_undo, local_redo, true, true, true, allowedTracks);
} else if (timeline->isClip(itemId)) {
    result = result && (timeline->requestClipMove(itemId, targetTrackId, targetPos, true, true, true, true, local_undo, local_redo) == TimelineModel::MoveSuccess);
} else {
    result = result && timeline->requestCompositionMove(itemId, targetTrackId, ..., targetPos, true, true, local_undo, local_redo);
}
timeline->requestClearSelection();
if (!result) {
    bool undone = local_undo();
    Q_ASSERT(undone);                                      // compensating rollback + assert, the pass-1 discipline
    pCore->displayMessage(i18n("Cannot move selected group"), ErrorMessage);
}
UPDATE_UNDO_REDO_NOLOCK(local_redo, local_undo, undo, redo);   // fold into the caller's accumulators only on success
```

**Flow:** (1) elect affected tracks: explicit list minus locked, or all target-flagged tracks (inactive targets are also removed from the insertion list so the new clip does not land on an inactive lane); (2) `breakAffectedGroups` on the full zone range (same helper as extract — groups spanning the boundary are broken on the unaffected side first); (3) OVERWRITE mode: `liftZone` on every affected track (mix-aware edge deletion per zone-extract-lift-kernel) — the old content is gone, no ripple; INSERT mode: cut the clip sitting at `insertFrame` on each track (so the hole starts on a clean boundary), then `requestInsertSpace` selects everything from `zone.x()` to the end of each allowed track and moves ONE representative by the POSITIVE delta through the ordinary move ladders onto private `local_undo/local_redo`; (4) on move failure the private pair is rolled back and asserted, and NOTHING is folded into the caller's accumulators (the whole zone op stays atomic); on success `UPDATE_UNDO_REDO_NOLOCK` folds the private pair in; (5) the new clip is planted via the standard `requestClipInsertion` functor ladder (pass 1), with an optional interactive audio-stream prompt that can create fresh audio tracks which are retroactively added to `affectedTracks`; (6) the public wrapper pushes one entry ("Insert zone"/"Overwrite zone") or runs `undo()` and reports failure.
**Invariant:** insert and overwrite share the same prelude (target election + breakAffectedGroups) and differ only in the middle stage (lift-all vs cut+ripple); the ripple is expressed as one representative move so every validation/availability/mix guard of the move ladders applies to the whole shift; a failed ripple rolls back its PRIVATE accumulator before anything is folded outward — the caller's undo chain never sees a half-applied zone op; empty item sets are successes (no-op), not errors.
**Probe:** NO direct test file covers insertZone/overwrite (grep over tests/ = 0 files) — evidence gap recorded; the underlying primitives it composes (cut, move ladders, insertion functor) are test-pinned by trimmingtest/movetest/modeltest (passes 1–2). Deterministic probe below executed live.

## Get live surrounding code
**Retrieve:**
```bash
$ grep -n 'requestInsertSpace\|removeSpace' src/timeline2/model/timelinefunctions.cpp
803:        result = TimelineFunctions::removeSpace(timeline, zone, undo, redo, tracks);
877:            result && TimelineFunctions::requestInsertSpace(timeline, QPoint(insertFrame, insertFrame + (zone.y() - zone.x())), undo, redo, affectedTracks);
975:bool TimelineFunctions::removeSpace(const std::shared_ptr<TimelineItemModel> &timeline, QPoint zone, Fun &undo, Fun &redo, const QVector<int> &allowedTracks,
1026:bool TimelineFunctions::requestInsertSpace(const std::shared_ptr<TimelineItemModel> &timeline, QPoint zone, Fun &undo, Fun &redo,
# executed live this pass; graph search_graph unavailable (MCP not connected in session)
```

## Verdict
Adopt the shared-prelude/split-middle shape: any "insert vs overwrite" pair should differ only in the middle stage so both inherit the same constraint-breaking and planting code. Adopt the private-accumulator-then-fold pattern (`local_undo/local_redo` + UPDATE_UNDO_REDO_NOLOCK only on success) whenever a composite must stay atomic against a caller's accumulator chain — it is the difference between "the ripple failed" and "the undo stack contains a half-shifted timeline". Adapt the target-flag election to your host's lane activation model; omit the interactive audio-stream prompt unless your host creates lanes mid-operation. Porting risk: no repo test covers either mode — add fixtures asserting (a) a group straddling the insert frame is broken and regrouped, (b) a failed ripple leaves the model byte-identical, (c) overwrite deletes inside-mix clips whole.
