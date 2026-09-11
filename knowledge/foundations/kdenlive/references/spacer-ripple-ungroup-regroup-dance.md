<!-- capsule-v2 -->
# Spacer ripple — how do you insert/remove space at a frame across tracks when groups span the operation boundary?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter must add "insert space" / "remove blank" (ripple) operations that shift every clip after a frame on one track (or all tracks), but user groups may straddle the operation position and multi-track groups must move as a unit or not at all.

## Start/end pair with module-static operation state + temporary group breaking
**Path/Symbol:** `src/timeline2/model/timelinefunctions.cpp:TimelineFunctions::requestSpacerStartOperation` (426–625) / `requestSpacerEndOperation` (627–746); module-statics `spacerUngroupedItems` (QMap leaf→parent), `spacerMinPosition`, `spacerMaxPosition` (75–77); accessors `spacerMinPos()`/`spacerMaxPos()` (3548/3553); callers `requestDeleteBlankAt` (2892–3000), `requestDeleteAllBlanksFrom` (3001–3105).
**Signature:** `static std::pair<int,int> requestSpacerStartOperation(const std::shared_ptr<TimelineItemModel> &timeline, int trackId, int position, bool ignoreMultiTrackGroups = false, bool allowGroupBreaking = false)` → `{anchorItemId, maxSpaceBefore}`; `static bool requestSpacerEndOperation(const std::shared_ptr<TimelineItemModel> &timeline, int itemId, int startPosition, int endPosition, int affectedTrack, int moveGuidesPosition, Fun &undo, Fun &redo, bool pushUndo = true)`.
**Data Shape:** start returns the ANCHOR item (first affected clip, earliest across tracks when trackId==-1) plus the maximum removable space before it; end takes the anchor's original `startPosition` and the target `endPosition` (end > start = insert, end < start = remove).

### Decisive source
```cpp
// timelinefunctions.cpp:445-536 — leaves of groups that sit BEFORE the operation position are
// temporarily ungrouped so the anchor can move without dragging the whole group
for (int l : leaves) {
    int pos = timeline->getItemPosition(l);
    int itemEnd = timeline->getItemEnd(l);
    bool outOfRange = itemEnd < position;
    bool unaffectedTrack = ignoreMultiTrackGroups && trackId > -1 && tid != trackId;
    if (allowGroupBreaking) {
        if (outOfRange || unaffectedTrack) { leavesToRemove.insert(l); } else { leavesToKeep.insert(l); }
    } else if (outOfRange) {
        // grouped clip before the spacer: compute relatedMaxSpace {blank_before, blank_after} per track
        ...
        relatedMaxSpace.insert(tid, {pos - lastPos, -1});   // clamp: group blocks further removal
    }
    if (!outOfRange && !unaffectedTrack) { /* firstClipOnTrack per track */ }
}
for (int l : leavesToRemove) {
    int checkedParent = timeline->m_groups->getDirectAncestor(l);
    if (checkedParent < 0) { checkedParent = l; }
    spacerUngroupedItems.insert(l, checkedParent);          // remember who to rejoin
}
if (leavesToKeep.size() == 1) { toSelect.insert(*leavesToKeep.begin()); groupsToRemove.insert(r); }
```
```cpp
// timelinefunctions.cpp:619-621 + 642-644 — transient snap point brackets the drag
spacerMinPosition = timeline->getItemPosition(firstCid) - spaceDuration;
timeline->m_snaps->addPoint(spacerMinPosition);             // view snaps to the blank edge
spacerMaxPosition = spaceAfterDuration > -1 ? spaceAfterDuration + timeline->getItemPosition(firstCid) : -1;
...
// requestSpacerEndOperation:
timeline->m_snaps->removePoint(spacerMinPosition);           // ALWAYS removed, even on failure paths
spacerMinPosition = -1;  spacerMaxPosition = -1;
```
```cpp
// timelinefunctions.cpp:688-745 — end = restore anchor, optional lift, then ONE group/clip move, then regroup
if (timeline->m_editMode == TimelineMode::OverwriteEdit && endPosition < startPosition) {
    liftOk = liftOk && TimelineFunctions::liftZone(timeline, target_track, QPoint(endPosition, startPosition), undo, redo);
    if (clips.size() > 1) { timeline->requestSetSelection(clips); mainGroup = timeline->m_groups->getRootId(itemId); }
}
if (liftOk && (mainGroup > -1 || clips.size() == 1)) {
    if (clips.size() > 1) { final = timeline->requestGroupMove(itemId, mainGroup, 0, endPosition - startPosition, true, true, undo, redo); ... cleanFakeState(); }
    else { final = timeline->requestClipMove(itemId, track, endPosition, true, true, true, true, undo, redo) == TimelineModel::MoveSuccess; ... setFakePosition(-1); }
}
...
// success only: regroup the temporarily ungrouped leaves into their remembered parents
while (i.hasNext()) { i.next();
    if (timeline->isItem(i.value())) {
        if (newlyGrouped.count(i.value()) > 0) { timeline->m_groups->setInGroupOf(i.key(), i.value(), local_undo, local_redo); }
        else { timeline->m_groups->groupItems({i.key(), i.value()}, local_undo, local_redo); newlyGrouped.insert(i.value()); }
    } else { /* parent is a group node: reattach via groupItems/setGroup */ }
}
spacerUngroupedItems.clear();
```

**Flow:** (1) start: locked track refuses (`flashLock`, returns {-1,-1}); `requestClearSelection()` FIRST (selection groups have no undo — see selection-group-lock-plane); collect items from `position` to end of track, expand each root group to its leaves; for every group, leaves ending BEFORE `position` are either recorded in `relatedMaxSpace` (they clamp how much space may be removed: the group's internal blank is untouchable) or, with `allowGroupBreaking=true`, removed from the group and parked in `spacerUngroupedItems` (leaf→directAncestor); a group reduced to one kept leaf is dissolved for the operation (the leaf is selected instead of the group); (2) compute `spaceDuration` = MINIMUM blank size at `clipPos-1` across all affected tracks (any non-blank track forces 0), clamped by `relatedMaxSpace`; register a TRANSIENT snap point at the blank edge; return `{anchorId, spaceDuration}`; (3) end: move guides if unlocked (`KdenliveSettings::lockedGuides()` gates this), remove the transient snap point, restore the anchor to its original position (it was dragged by the view), optionally `liftZone` the removed range in OverwriteEdit mode (lift destroys selection groups → re-select and recompute the root), then perform EXACTLY ONE ripple: `requestGroupMove(root, delta)` for multi-item selections or `requestClipMove(anchor, endPosition)` for a single item — both as pass-1 primitives feeding the shared undo/redo accumulators; (4) only on success push undo ("Insert space" / "Remove space" by direction) and regroup the parked leaves back into their remembered parents (setInGroupOf when the parent was already re-gathered, groupItems otherwise); on failure run `undo()` and leave the statics cleared.
**Invariant:** the module-statics are single-operation state: `spacerUngroupedItems` is cleared at start AND after successful regroup, `spacerMinPosition` is always removed from the snap model before being reset (callers that abandon mid-loop call `m_snaps->removePoint(spacerMinPosition)` themselves — see requestDeleteAllBlanksFrom), and the regroup step runs ONLY on success so a failed ripple never half-heals group membership. `requestDeleteBlankAt` refuses outright when the two clips flanking the blank belong to the SAME group (getItemsInRange over the blank span has size 2 and shared root). `requestDeleteAllBlanksFrom` walks `getNextBlankStart` and folds each per-blank local undo into ONE stack entry via `UPDATE_UNDO_REDO_NOLOCK`; a blank blocked by a group is skipped (`blankStart = start`), not fatal.
**Probe:** `tests/spacertest.cpp` (whole 244L): plain remove-all-blanks shifts 10/80/101 → 10/30/50; same-track group {cid2,cid3} makes cid3 land at 51 (one frame preserved inside the group); cross-track group {cid2@tid1, cid4@tid2} REJECTS the move for the grouped clip (cid2 stays 80, cid3 → 100); group {cid1,cid4} moves as a unit (cid4 20→10); `requestDeleteBlankAt` between two same-group clips returns false; the raw start/end pair inserts exactly +100 frames and undo restores state1 byte-for-byte.

## Get live surrounding code
**Retrieve:**
```bash
$ grep -n 'spacerUngroupedItems\|spacerMinPosition\|spacerMaxPosition' src/timeline2/model/timelinefunctions.cpp
75:QMap<int, int> spacerUngroupedItems;
76:int spacerMinPosition(-1);
77:int spacerMaxPosition(-1);
439:    spacerMinPosition = -1;
440:    spacerMaxPosition = -1;
445:        spacerUngroupedItems.clear();
536:                    spacerUngroupedItems.insert(l, checkedParent);
560:        QMapIterator<int, int> i(spacerUngroupedItems);
619:        spacerMinPosition = timeline->getItemPosition(firstCid) - spaceDuration;
620:        timeline->m_snaps->addPoint(spacerMinPosition);
621:        spacerMaxPosition = spaceAfterDuration > -1 ? spaceAfterDuration + timeline->getItemPosition(firstCid) : -1;
642:    timeline->m_snaps->removePoint(spacerMinPosition);
643:    spacerMinPosition = -1;
644:    spacerMaxPosition = -1;
718:        QMapIterator<int, int> i(spacerUngroupedItems);
743:        spacerUngroupedItems.clear();
3036:                timeline->m_snaps->removePoint(spacerMinPosition);
3084:                timeline->m_snaps->removePoint(spacerMinPosition);
3548:    return spacerMinPosition;
3553:    return spacerMaxPosition;
# executed live this pass; graph search_graph unavailable (MCP not connected in session)
```

## Verdict
Adopt the start/end split with explicit operation state: it lets a view drive a live drag (fake positions, transient snap point, min/max bounds exposed via accessors) while the model commits exactly one undoable primitive at the end. Adopt the temporary-ungroup/regroup dance with a leaf→parent parking map — it is the only way a ripple can pass THROUGH a group boundary without moving the pre-boundary members, and the success-only regroup keeps membership atomic. Adopt the relatedMaxSpace clamp (grouped neighbors define the removable-space ceiling) and the same-group-blank refusal. Adapt the module-statics to per-operation objects in a threaded host (they are process-global here and assume one drag at a time); omit the guide-moving and subtitle-layer branches unless your host has those concepts.
