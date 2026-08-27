<!-- capsule-v2 -->
# Zone extract/lift kernel — how do you delete (or delete-and-collapse) a frame range across several tracks as ONE undoable operation when groups span the range boundary?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter needs "extract zone" (delete the range AND ripple everything after it left) and "lift zone" (delete the range, leave the hole) as single undo entries across multiple tracks, where user groups may straddle the range edge and clips at the edges may sit inside same-track mixes.

## breakAffectedGroups + extractZoneWithUndo orchestration + mix-aware liftZone + single-move removeSpace ripple
**Path/Symbol:** `src/timeline2/model/timelinefunctions.cpp:TimelineFunctions::breakAffectedGroups` (751–771), `extractZone` push wrapper (777–785), `extractZoneWithUndo` (787–807), `liftZone` (911–973), `removeSpace` (975–1024); callers `src/timeline2/view/timelinecontroller.cpp:795–810` (extract with mix-adjusted in/out), `:3440–3470` (liftOnly variant + guide move), `:3520–3560` (per-clip group extraction); spacer end-operation liftZone call sites timelinefunctions.cpp:668/:673.
**Signature:** `static bool breakAffectedGroups(const std::shared_ptr<TimelineItemModel> &timeline, const QVector<int> &tracks, QPoint zone, Fun &undo, Fun &redo)`; `static bool extractZoneWithUndo(const std::shared_ptr<TimelineItemModel> &timeline, const QVector<int> &tracks, QPoint zone, bool liftOnly, int clipToUnGroup, std::unordered_set<int> clipsToRegroup, Fun &undo, Fun &redo)`; `static bool liftZone(const std::shared_ptr<TimelineItemModel> &timeline, int trackId, QPoint zone, Fun &undo, Fun &redo)`; `static bool removeSpace(const std::shared_ptr<TimelineItemModel> &timeline, QPoint zone, Fun &undo, Fun &redo, const QVector<int> &allowedTracks, bool useTargets = false)`.
**Data Shape:** `QPoint(zone.x(), zone.y())` = [startFrame, endFrame) in absolute frames; every stage appends its own lambdas to the SAME `Fun &undo`/`Fun &redo` accumulators so the whole zone op is one stack entry.

### Decisive source
```cpp
// timelinefunctions.cpp:751-771 — ungroup ONLY the leaves that are NOT on affected tracks
for (auto trackId : tracks) {
    std::unordered_set<int> items = timeline->getItemsInRange(trackId, zone.x(), zone.y());
    affectedItems.insert(items.begin(), items.end());
}
for (int item : affectedItems) {
    if (timeline->m_groups->isInGroup(item)) {
        int groupId = timeline->m_groups->getRootId(item);
        std::unordered_set<int> all_children = timeline->m_groups->getLeaves(groupId);
        for (int child : all_children) {
            int childTrackId = timeline->getItemTrackId(child);
            if (!tracks.contains(childTrackId) && timeline->m_groups->isInGroup(child)) {
                // This item should not be affected by the operation, ungroup it
                result = result && timeline->requestClipUngroup(child, undo, redo);
            }
        }
    }
}
```
```cpp
// timelinefunctions.cpp:787-807 — the whole operation is one accumulator chain
if (clipToUnGroup > -1) {
    result = timeline->requestClipUngroup(clipToUnGroup, undo, redo);
}
result = breakAffectedGroups(timeline, tracks, zone, undo, redo);
for (auto trackId : tracks) {
    if (timeline->getTrackById_const(trackId)->isLocked()) { continue; }   // locked tracks skipped, not failed
    result = result && TimelineFunctions::liftZone(timeline, trackId, zone, undo, redo);
}
if (result && !liftOnly) {
    result = TimelineFunctions::removeSpace(timeline, zone, undo, redo, tracks);   // extract = lift + collapse
}
if (clipsToRegroup.size() > 1) {
    result = timeline->requestClipsGroup(clipsToRegroup, undo, redo);              // regroup only what was parked
}
```
```cpp
// timelinefunctions.cpp:911-944 — liftZone: mix-aware cut at BOTH edges; inside-mix ⇒ delete whole clip
if (mixData.first.firstClipId > -1) {   // start clip has a start mix
    if (mixData.first.secondClipInOut.first + (mixData.first.firstClipInOut.second - mixData.first.secondClipInOut.first) -
            mixData.first.mixOffset >= zone.x()) {
        abortCut = true;                 // cut pos lands INSIDE the mix zone after cutting
    }
}
if (!abortCut) {
    TimelineFunctions::requestClipCut(timeline, startClipId, zone.x(), undo, redo);
} else {
    // Remove the clip now, so that the mix is deleted before checking items in range
    timeline->requestClipUngroup(startClipId, undo, redo);
    timeline->requestItemDeletion(startClipId, undo, redo);
}
...
std::unordered_set<int> clips = timeline->getItemsInRange(trackId, zone.x(), zone.y());
for (const auto &clipId : clips) {
    if (timeline->isInGroup(clipId)) {
        timeline->requestClipUngroup(clipId, undo, redo, true);   // ungroup BEFORE delete
    }
    timeline->requestItemDeletion(clipId, undo, redo);
}
```
```cpp
// timelinefunctions.cpp:975-1024 — removeSpace: ONE representative move ripples everything after the zone
std::unordered_set<int> subs = timeline->getItemsInRange(target_track, zone.y() - 1, -1, true);  // from zone end to ∞
...
timeline->requestSetSelection(clips);
int targetPos = timeline->getItemPosition(itemId) + zone.x() - zone.y();   // negative delta = left
if (timeline->m_groups->isInGroup(itemId)) {
    result = timeline->requestGroupMove(itemId, timeline->m_groups->getRootId(itemId), 0, zone.x() - zone.y(), true, true, undo, redo, true, true, true, allowedTracks);
} else if (timeline->isClip(itemId)) {
    result = timeline->requestClipMove(itemId, targetTrackId, targetPos, true, true, true, true, undo, redo) == TimelineModel::MoveSuccess;
} else if (timeline->isComposition(itemId)) {
    result = timeline->requestCompositionMove(itemId, targetTrackId, ..., targetPos, true, true, undo, redo);
}
timeline->requestClearSelection();
if (!result) { undo(); }
```
```cpp
// timelinecontroller.cpp:795-810 — caller adjusts the zone for mixes BEFORE calling extract
if (mixData.first.firstClipId > -1) {
    in += (mixData.first.firstClipInOut.second - mixData.first.secondClipInOut.first - mixData.first.mixOffset);
}
if (mixData.second.firstClipId > -1) {
    out -= mixData.second.mixOffset;
}
TimelineFunctions::extractZoneWithUndo(m_model, tracks, QPoint(in, out), false, clipToUngroup, clipsToRegroup, undo, redo);
pCore->pushUndo(undo, redo, i18n("Extract zone"));
```

**Flow:** (1) `breakAffectedGroups` first: for every item inside the zone that belongs to a group, walk the group's leaves and ungroup exactly those leaves whose track is NOT in the affected set — a group spanning the boundary is broken only on the unaffected side, so the affected side can be deleted/moved without dragging the rest of the group; (2) per-track `liftZone`: at each edge, if the edge clip has a mix and the cut position would land inside the mix overlap after cutting, ABORT the cut and delete the whole clip instead (ungroup first, then delete, so the mix registry is cleaned before the in-range scan); otherwise cut at the edge frame; then delete every remaining item in range, ungrouping grouped ones first; locked tracks are SKIPPED (their content survives the zone op); (3) if this is an extract (not lift-only), `removeSpace` selects every item from `zone.y()-1` to the end of each allowed track and moves ONE representative item by the negative delta — the group/clip/composition move machinery (pass 1–2 ladders) then ripples the rest through validation, availability checks, and their own functors onto the same accumulators; (4) `clipsToRegroup` (the leaves parked by the caller, e.g. the controller's extract path) are re-grouped only when more than one remains; (5) the public wrapper pushes the whole accumulated pair as ONE undo entry ("Extract zone"/"Lift zone"); the controller's liftOnly variant additionally moves/deletes guides in the same entry when all tracks are affected.
**Invariant:** one zone operation = one undo entry built by appending stage functors to shared accumulators; groups never constrain the operation because out-of-range leaves are ungrouped FIRST (and regrouped last, success-only); a clip whose cut position falls inside its own mix is deleted whole rather than cut (no half-mixes survive); locked tracks are exempt, not errors; the collapse step reuses the ordinary move ladders (so all their validation/rollback discipline applies) instead of moving items directly.
**Probe:** NO direct test file exists for the zone plane (`grep -rln 'extractZone\|liftZone' tests/` = 0 files) — evidence gap recorded; source-anchored via the call graph above (spacer end-op reuses liftZone at :668/:673, pass 3). Deterministic probe below executed live.

## Get live surrounding code
**Retrieve:**
```bash
$ grep -n 'breakAffectedGroups\|extractZoneWithUndo\|liftZone' src/timeline2/model/timelinefunctions.cpp
668:                    liftOk = liftOk && TimelineFunctions::liftZone(timeline, target_track, QPoint(endPosition, startPosition), undo, redo);
673:            liftOk = liftOk && TimelineFunctions::liftZone(timeline, affectedTrack, QPoint(endPosition, startPosition), undo, redo);
751:bool TimelineFunctions::breakAffectedGroups(const std::shared_ptr<TimelineItemModel> &timeline, const QVector<int> &tracks, QPoint zone, Fun &undo, Fun &redo)
782:    bool res = extractZoneWithUndo(timeline, tracks, zone, liftOnly, clipToUnGroup, clipsToRegroup, undo, redo);
787:bool TimelineFunctions::extractZoneWithUndo(const std::shared_ptr<TimelineItemModel> &timeline, const QVector<int> &tracks, QPoint zone, bool liftOnly,
795:    result = breakAffectedGroups(timeline, tracks, zone, undo, redo);
800:        result = result && TimelineFunctions::liftZone(timeline, trackId, zone, undo, redo);
857:    result = breakAffectedGroups(timeline, affectedTracks, QPoint(insertFrame, insertFrame + (zone.y() - zone.x())), undo, redo);
861:            result = result && TimelineFunctions::liftZone(timeline, target_track, QPoint(insertFrame, insertFrame + (zone.y() - zone.x())), undo, redo);
911:bool TimelineFunctions::liftZone(const std::shared_ptr<TimelineItemModel> &timeline, int trackId, QPoint zone, Fun &undo, Fun &redo)
# executed live this pass; graph search_graph unavailable (MCP not connected in session)
```

## Verdict
Adopt the staged-accumulator pattern for any multi-track rectangular edit: break constraints first (ungroup out-of-range leaves), apply the local mutation per track, then express the global ripple as ONE representative move through your existing validated move machinery — never hand-roll the ripple. Adopt the inside-mix abort rule (delete whole rather than cut into an overlap) as the template for any "cut at frame" primitive coexisting with transition zones. Adopt skip-not-fail for locked/exempt lanes. Adapt the QPoint zone to your host's range type; omit the guide-model side effects unless your host has guides. Porting risk: no repo test covers extract/lift — add fixtures with a group straddling the zone edge and a clip whose cut lands inside a mix before relying on the abort branch.
