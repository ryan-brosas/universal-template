<!-- capsule-v2 -->
# Selection & lock plane — how do you represent a multi-item selection so it moves/deletes atomically with user groups, and how do you gate every mutation behind an undoable track lock?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter must let the user select N items on different tracks and move/delete them as one unit, while user-created groups keep their own undoable membership — and must make "locked track" a first-class gate that every mutation entry point honors but that is itself undoable.

## Selection as a GroupType::Selection node in the SAME forest, created without undo
**Path/Symbol:** `src/timeline2/model/timelinemodel.cpp:TimelineModel::requestSetSelection` (7614–7664), `requestClearSelection(bool)` (7442–7500) + undoable variant (7526–7538), `getCurrentSelection` (7549–7563), `requestAddToSelection` (7565–7612), `requestRemoveFromSelection` (7596–7612), `checkAndUpdateOffset` (7666–7695), `requestClipsGroup` guards (5037–5110); lock plane: `setTrackLockedState` (7739+), `trackIsLocked` (8303–8310), guard sites 2899/3947/4465/4808/4966/5004; `TrackModel::isLocked` sites trackmodel.cpp 309/488/715/758/797/1425/1437/1452/1477/1532/1610/1868.
**Signature:** `bool requestSetSelection(const std::unordered_set<int> &ids)`; `void requestAddToSelection(int itemId, bool clear, bool singleSelect)`; `void setTrackLockedState(int trackId, bool lock)`; `bool trackIsLocked(int trackId) const`.
**Data Shape:** `m_currentSelection` holds EITHER one group id (a GroupType::Selection node) OR a set of item ids; `getCurrentSelection()` always expands a selection group to its leaves; `m_singleSelectionMode` is a sticky flag toggled by singleSelect clicks.

### Decisive source
```cpp
// timelinemodel.cpp:7614-7664 — multi-root selection becomes a Selection-typed group node
bool TimelineModel::requestSetSelection(const std::unordered_set<int> &ids) {
    if (m_currentSelection.size() > 0) { requestClearSelection(); }
    ...
    std::transform(ids.begin(), ids.end(), std::inserter(roots, roots.begin()), [&](int id) { return m_groups->getRootId(id); });
    if (roots.size() == 0) { m_currentSelection.clear(); }
    else if (roots.size() == 1) { m_currentSelection = {sid}; setSelected(...); if (isGroup(sid)) checkAndUpdateOffset(childIds); }
    else {
        Fun undo = []() { return true; };          // LOCAL accumulators — never pushed to the stack
        Fun redo = []() { return true; };
        if (ids.size() == 2) { checkAndUpdateOffset(pairIds); }   // same-bin pair → display offset
        int groupId = m_groups->groupItems(ids, undo, redo, GroupType::Selection);
        if (groupId > -1) { m_currentSelection = {groupId}; result = true; }
    }
    Q_EMIT selectionChanged();
    return result;
}
```
```cpp
// timelinemodel.cpp:7442-7500 — clearing selection DESTRUCTS the selection group (no undo)
if (isGroup(*m_currentSelection.begin())) {
    for (auto &id : items) { ... setGrab(false); setSelected(false); ...
        if (m_groups->getType(*m_currentSelection.begin()) == GroupType::Selection) {
            m_groups->destructGroupItem(*m_currentSelection.begin());   // membership gone, silently
        }
    }
}
m_currentSelection.clear();
Q_EMIT selectionChanged();
```
```cpp
// timelinemodel.cpp:5037-5059 — user grouping REFUSES the Selection type; only requestSetSelection may create it
int TimelineModel::requestClipsGroup(const std::unordered_set<int> &ids, bool logUndo, GroupType type) {
    if (type == GroupType::Selection || type == GroupType::Leaf) { return -1; }   // "Call requestSetSelection instead"
    ...
}
int TimelineModel::requestClipsGroup(const std::unordered_set<int> &ids, Fun &undo, Fun &redo, GroupType type) {
    if (type != GroupType::Selection) { requestClearSelection(); }   // user grouping clears the transient selection
    ...
    if (type != GroupType::Selection) { PUSH_FRONT_LAMBDA(unselect, undo); PUSH_FRONT_LAMBDA(unselect, redo); }
}
```
```cpp
// timelinemodel.cpp:7739-7770 + 8303-8310 — the lock is itself an undoable model operation
Fun lock_lambda = [this, trackId]() { lockTrack(trackId, true); return true; };
Fun unlock_lambda = [this, trackId]() { lockTrack(trackId, false); return true; };
if (lock) { if (lock_lambda()) { UPDATE_UNDO_REDO(lock_lambda, unlock_lambda, undo, redo); PUSH_UNDO(undo, redo, i18n("Lock track")); } }
...
bool TimelineModel::trackIsLocked(int trackId) const {
    if (trackId == -1 && m_subtitleModel) { return m_subtitleModel->isLocked(); }   // subtitle pseudo-track
    return getTrackById_const(trackId)->isLocked();
}
```

**Flow:** (1) selecting multiple items from DIFFERENT roots calls `m_groups->groupItems(ids, localUndo, localRedo, GroupType::Selection)` — the same forest kernel as user groups (see groups-forest-updown-links) but with throwaway accumulators: the selection group's creation/destruction is deliberately NOT on the undo stack, so Ctrl-Z can never resurrect or erase a selection; (2) every consumer goes through `getCurrentSelection()` which expands the selection node to leaves, so move/delete/cut code sees a flat id set regardless of representation; (3) `requestClearSelection` destructs the selection node and resets per-item grab/selected flags; the undoable variant captures the current leaves and reverses via `requestSetSelection(clips)`; (4) `requestAddToSelection(itemId, clear, singleSelect)`: singleSelect replaces the whole set and latches `m_singleSelectionMode` (the flag the group-move kernel reads to rebuild a temporary group from the current selection); non-single adds one id and re-runs requestSetSelection; (5) `requestRemoveFromSelection` removes the item's WHOLE non-selection parent group when the item sits inside a user group (you cannot deselect half of a group); (6) locks: `setTrackLockedState` pushes an undoable Lock/Unlock command; every mutation entry point checks `trackIsLocked`/`TrackModel::isLocked` BEFORE validating (insertion functors at trackmodel.cpp:309/488 take a `bypassLock` escape hatch used by internal replants; resize decision branches return false at :715/:758/:797; deletion/move/resize entries at timelinemodel.cpp:2899/3947/4465/4808/4966/5004 refuse with `flashLock` emission for UI feedback); `KdenliveSettings::lockedGuides()` separately gates guide movement inside spacer end-operations.
**Invariant:** a GroupType::Selection node exists ONLY between requestSetSelection and the next clear — it is never pushed to the undo stack, so any composite that mutates items must `requestClearSelection()` FIRST or its undo would reference a destroyed group id (this is why clip-cut-group-split-dance and spacer start both clear selection first); `requestClipsGroup` refuses Selection/Leaf types so user groups and selections can never be confused; `getCurrentSelection()` is the single expansion point; a locked track rejects at the ENTRY point (typed failure, no partial mutation) while internal primitives use `bypassLock` so replant/reverse ladders are not blocked by the very operation they serve.
**Probe:** `tests/modeltest.cpp:2035-2295` "Operations under locked tracks": insertion into a locked track returns false with cid==-1 and clip count unchanged; move refused (position frozen); `requestItemResize` returns -1 for BOTH shrink and grow; composition move/resize refused; bin-clip deletion refused while locked; after `setTrackLockedState(tid, false)` every same call succeeds; `checkConsistency()` green after every step.

## Get live surrounding code
**Retrieve:**
```bash
$ grep -n 'GroupType::Selection' src/timeline2/model/timelinemodel.cpp
3716:            if (m_groups->getType(current_group) == GroupType::Selection) {
5041:    if (type == GroupType::Selection || type == GroupType::Leaf) {
5059:    if (type != GroupType::Selection) {
5081:    if (type == GroupType::Selection && ids.size() == 1) {
5106:    if (type != GroupType::Selection) {
5160:    bool isSelection = m_groups->getType(m_groups->getRootId(itemId)) == GroupType::Selection;
5179:    bool isSelection = type == GroupType::Selection;
7475:            if (m_groups->getType(*m_currentSelection.begin()) == GroupType::Selection) {
7602:    if (parentGroup > -1 && m_groups->getType(parentGroup) != GroupType::Selection) {
7650:        int groupId = m_groups->groupItems(ids, undo, redo, GroupType::Selection);
$ grep -n 'setTrackLockedState\|trackIsLocked' src/timeline2/model/timelinemodel.cpp | head -15
68:        .method("setTrackLockedState", &TimelineModel::setTrackLockedState)(parameter_names("trackId", "lock"))
2899:            if (trackIsLocked(old_trackId)) {
3947:        if (tid > -1 && trackIsLocked(tid)) {
4465:        if (trackId > -1 && trackIsLocked(trackId)) {
4808:        if (trackId > -1 && trackIsLocked(trackId)) {
4966:        if (tid > -1 && trackIsLocked(tid)) {
5004:        if (tid > -1 && trackIsLocked(tid)) {
7739:void TimelineModel::setTrackLockedState(int trackId, bool lock)
8303:bool TimelineModel::trackIsLocked(int trackId) const
# executed live this pass; graph search_graph unavailable (MCP not connected in session)
```

## Verdict
Adopt selection-as-group-node: reusing the user-group forest gives atomic multi-track move/delete for free (one requestGroupMove covers the selection root) and the no-undo discipline makes selection invisible to the document history. Adopt the single expansion point (getCurrentSelection) and the type refusal in requestClipsGroup — they are what keep the two group kinds from leaking into each other. Adopt the lock as an undoable state command plus entry-point guards with a bypass flag for internal replants; adapt the flashLock signal to your host's feedback channel. Omit the same-bin offset display (checkAndUpdateOffset) unless you port the dual-clip AV display feature.
