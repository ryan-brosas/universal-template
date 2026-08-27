<!-- capsule-v2 -->
# Clip cut — how do you split one clip at a frame while every group it belongs to (AV split, user groups) stays intact and undoable?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter must cut a clip at an arbitrary frame; the clip may be half of an AV split, inside user groups, carry a mix end, and the whole operation must be ONE undo step that also splits the group hierarchy.

## Group-scoped cut + per-clip clone-resize-move + group-tree split
**Path/Symbol:** `src/timeline2/model/timelinefunctions.cpp:TimelineFunctions::requestClipCut` (258–364), `processClipCut` (150–237), `requestClipCutAll` (366–424), `cloneClip` (80–112); group-tree split in `src/timeline2/model/groupsmodel.cpp:GroupsModel::split` (483–625).
**Signature:** `bool requestClipCut(const std::shared_ptr<TimelineItemModel> &timeline, int clipId, int position, Fun &undo, Fun &redo)` / `bool processClipCut(..., int &newId, Fun &undo, Fun &redo)` / `bool GroupsModel::split(int id, const std::function<bool(int)> &criterion, Fun &undo, Fun &redo)`.
**Data Shape:** one shared `Fun &undo/Fun &redo` accumulator threaded through every stage; `clipsToCut` = ids where `start < position < start+duration`; `topElements` = set of `getRootId(cid)` for all cut clips; `newIds` = clones.

### Decisive source
```cpp
// timelinefunctions.cpp:295-350 — order of operations is the contract
// We need to call clearSelection before attempting the split or the group split will be corrupted by the selection group (no undo support)
timeline->requestClearSelection();
...
for (int cid : std::as_const(clipsToCut)) {
    count++;
    int newId = -1;
    bool res = processClipCut(timeline, cid, position, newId, undo, redo);
    if (!res) { bool undone = undo(); Q_ASSERT(undone); return false; }
    // splitted elements go temporarily in the same group as original ones.
    timeline->m_groups->setInGroupOf(newId, cid, undo, redo);
    newIds << newId;
}
if (count > 0 && timeline->m_groups->isInGroup(clipId)) {
    // we now split the group hierarchy.
    // As a splitting criterion, we compare start point with split position
    auto criterion = [timeline, position](int cid) { return timeline->getItemPosition(cid) < position; };
    for (const int topId : topElements) {
        res = res && timeline->m_groups->split(topId, criterion, undo, redo);
    }
    if (!res) { bool undone = undo(); Q_ASSERT(undone); return false; }
}
```
```cpp
// groupsmodel.cpp:483-524 — split copies the subtree with temporary NEGATIVE ids before touching the real tree
Q_ASSERT(m_upLink[id] == -1);            // valid only for roots
Q_ASSERT(m_groupIds[id] != GroupType::Selection);
std::unordered_map<int, int> corresp;    // real id -> temp negative id
std::vector<int> to_move;                // leaves going to the new tree
std::unordered_map<int, std::unordered_set<int>> new_groups;
std::queue<int> queue; queue.push(id);   // BFS over downLink
while (!queue.empty()) { ... if (!isLeaf(current) || criterion(current)) { ... } }
// then: destructGroupItem(each moved leaf) -> recreate leaves -> prune empty temp groups
//       -> rebuild bottom-up with groupItems(group, undo, redo, type, true)
```

**Flow:** (1) scope = `getGroupElements(clipId)` minus locked-track clips (subtitles always allowed, but two overlapping subtitles at one position are refused with a message + rollback); (2) remember which track/sub-layer to reselect AFTER the cut; (3) `requestClearSelection()` FIRST — selection groups have no undo support and would corrupt the split; (4) per cut clip `processClipCut`: `cloneClip` (carries speed/warp_pitch/effects via `passTimelineProperties`), resize original to `position-start`, reassign any end mix to the clone (`reAssignEndMix` + playlist switch when no start mix), `cleanFadeEffects` on both stacks, resize clone, `requestClipMove(clone, track, position)`; if track duration changed push an `updateDuration` lambda; (5) each clone joins the original's group via `setInGroupOf(newId, cid)`; (6) only then `GroupsModel::split(root, pos<position)` per top root: BFS-copy subtree into temp-negative-id maps, destruct moved leaves from the old tree, recreate them, prune empty temp groups, rebuild bottom-up with `groupItems` preserving each node's `GroupType`; (7) reselect the right-hand fragment. `requestClipCutAll` walks subtitle layers then every unlocked track's `getClipByPosition(position)` through the SAME accumulator — one "Cut all clips" undo entry; any failure undoes ALL cuts made so far and asserts.
**Invariant:** the cut is atomic across the whole group scope — any stage failure runs the shared `undo()` and Q_ASSERTs it succeeded; clones are grouped BEFORE the tree split so the split criterion sees them; `GroupsModel::split` asserts root-only and non-Selection; AV-split halves keep their `GroupType::AVSplit` wrapper after the cut.
**Probe:** `tests/trimmingtest.cpp:444-531` "Cut should preserve AV groups": VideoOnly/AudioOnly pair under one AVSplit group cut at pos+4 → both halves each get their own AVSplit group with correct positions/states; `undoStack->undo()` restores the pre-cut state exactly, redo reproduces it. `tests/mixtest.cpp:177-210` pins playlist bookkeeping: cutting a mix-end clip keeps original AND clone on playlist 0; cutting a mix-start clip keeps original on playlist 1, clone on 0.

## Get live surrounding code
**Retrieve:**
```bash
$ grep -n 'requestClipCut\|processClipCut' src/timeline2/model/timelinefunctions.cpp
150:bool TimelineFunctions::processClipCut(...)
239:bool TimelineFunctions::requestClipCut(std::shared_ptr<TimelineItemModel> timeline, int clipId, int position)
258:bool TimelineFunctions::requestClipCut(const std::shared_ptr<TimelineItemModel> &timeline, int clipId, int position, Fun &undo, Fun &redo)
332:        bool res = processClipCut(timeline, cid, position, newId, undo, redo);
366:bool TimelineFunctions::requestClipCutAll(std::shared_ptr<TimelineItemModel> timeline, int position)
$ grep -n 'GroupsModel::split' src/timeline2/model/groupsmodel.cpp
483:bool GroupsModel::split(int id, const std::function<bool(int)> &criterion, Fun &undo, Fun &redo)
# executed live this pass; graph search_graph unavailable (MCP not connected in session)
```

## Verdict
Adopt the three-stage shape verbatim: clear selection → per-item clone/resize/move with one shared accumulator → root-only group-tree split by position criterion with temp-id BFS copy. Adopt the "clone joins the group BEFORE the split" ordering — it is what makes the criterion total. Adapt `cloneClip`'s effect-stack import to your host's effect model; omit the subtitle-layer walk unless you port subtitles. The temp-negative-id copy/prune/rebuild in `GroupsModel::split` is the reusable kernel for ANY "partition this tree by predicate" operation.
