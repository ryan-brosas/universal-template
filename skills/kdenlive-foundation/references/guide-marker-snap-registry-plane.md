<!-- capsule-v2 -->
# Guide/marker snap registry — how do you keep a secondary item model snap-integrated across consumers whose lifetimes you do not control, with fps-independent storage and range end-point snaps?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter must let guide markers feed every snap grid in the app — including grids created AFTER the markers — without the marker model holding owning pointers to grids that may die first, and without storing frame positions that break when the project fps changes.

## weak_ptr snap registry with dead-model pruning + GenTime storage + range end-point bookkeeping
**Path/Symbol:** `src/bin/model/markerlistmodel.cpp:MarkerListModel::addSnapPoint` (667–679), `removeSnapPoint` (681–693), `registerSnapModel` (838–852+), `addMarker` Fun variant (223–245), `addMarkers`/public `addMarker` (247–289), `removeMarker` pair (291–318), `editMarker` pair (320–455), `addMarker_lambda` (570–585), `addOrUpdateRangeMarker_lambda` (587–625), `deleteMarker_lambda` (625–646); `src/bin/model/markerlistmodel.hpp:241` (`std::vector<std::weak_ptr<SnapInterface>> m_registeredSnaps`); `src/timeline2/model/timelinemodel.cpp:226` (timeline registers its snap grid at construction).
**Signature:** `void addSnapPoint(GenTime pos)`; `void removeSnapPoint(GenTime pos)`; `void registerSnapModel(const std::weak_ptr<SnapInterface> &snapModel)`; `bool addMarker(GenTime pos, const QString &comment, int type, Fun &undo, Fun &redo)`; `bool editMarker(GenTime oldPos, GenTime pos, QString comment, int type, GenTime duration)`.
**Data Shape:** `m_markerList: std::map<int, CommentedTime>` (id→marker; CommentedTime carries GenTime pos + duration in SECONDS) + `m_markerPositions: QMap<int frame, int mid>` — a derived frame-projected index recomputed with `pCore->getCurrentFps()` at every access. Snap points: marker start always; marker start+duration when it is a range marker.

### Decisive source
```cpp
// markerlistmodel.cpp:667-679 — every push sweeps the registry, prunes dead models,
// and writes the pruned vector back via std::swap. No owning pointers anywhere.
void MarkerListModel::addSnapPoint(GenTime pos)
{
    QWriteLocker locker(&m_lock);
    std::vector<std::weak_ptr<SnapInterface>> validSnapModels;
    for (const auto &snapModel : m_registeredSnaps) {
        if (auto ptr = snapModel.lock()) {
            validSnapModels.push_back(snapModel);
            ptr->addPoint(pos.frames(pCore->getCurrentFps()));
        }
    }
    // Update the list of snapModel known to be valid
    std::swap(m_registeredSnaps, validSnapModels);
}
```
```cpp
// markerlistmodel.cpp:838-852 — late-registered grids are back-filled with ALL existing
// markers, including range end points.
void MarkerListModel::registerSnapModel(const std::weak_ptr<SnapInterface> &snapModel)
{
    READ_LOCK();
    if (auto ptr = snapModel.lock()) {
        m_registeredSnaps.push_back(snapModel);
        QMap<int, int>::const_iterator i = m_markerPositions.constBegin();
        while (i != m_markerPositions.constEnd()) {
            ptr->addPoint(i.key());
            if (m_markerList.at(i.value()).hasRange()) {
                ptr->addPoint(i.key() + m_markerList.at(i.value()).duration().frames((pCore->getCurrentFps())));
            }
```

**Flow:** every mutation lambda (add/delete/edit/move) is paired with the exact snap-point bookkeeping: add ⇒ `addSnapPoint(pos)` (+ end point if duration>0); delete ⇒ `removeSnapPoint(pos)` (+ end point); move (position change) ⇒ erase+reinsert with a NEW id (`TimelineModel::getNextId()`) and full snap swap; resize (duration change) ⇒ remove old end point, add new end point, start point untouched. Same-position add = rename: `addMarker` Fun variant detects `hasMarker(pos)` and builds `addOrUpdateRangeMarker_lambda` for BOTH undo and redo instead of insert/delete pairs. `editMarker` short-circuits no-ops (`oldPos == pos && comment/type/duration unchanged ⇒ true` with no undo entry).
**Invariant:** the set of snap points in every live registered grid always equals {marker starts} ∪ {range-marker end points}; storage is fps-independent (GenTime seconds), only the projected index and snap points are frame-valued — which is why profile fps switches preserve guide positions in seconds (test-pinned); a dead grid never blocks a push (weak_ptr lock + prune).
**Probe:** `tests/markertest.cpp` (501L whole): `checkMarkerList(model, list, snaps)` asserts the snap mirror after EVERY step; a second SnapModel registered mid-test receives the full back-fill; "Duration-based markers" pins point↔range conversion and end-point snaps; "Fps change guides [FpsChange]" pins seconds-invariance across 25→50→25 fps with frame recomputation (25↔50).

## Get live surrounding code
**Retrieve:**
```
grep -n "addSnapPoint\|removeSnapPoint\|registerSnapModel" src/bin/model/markerlistmodel.cpp
```
Executed byte-for-byte (pass 5, pin 62d6b0b79c51): hits at 363, 365, 373, 375, 382, 385, 405, 407, 415, 417, 423, 426, 582, 602, 605, 616, 618, 637, 639, 667, 681, 838 — every mutation site paired with snap bookkeeping, plus the registry entry points, exactly as cited.

## Verdict
Adopt the weak_ptr registry + prune-on-push pattern for any cross-model notification fan-out with uncontrolled consumer lifetimes, the GenTime-storage/frame-projection split for fps resilience, and the strict mutation↔snap-point pairing discipline. Adapt `SnapInterface` to your host's snap abstraction; the frame index can become a plain recomputed map. Omit the Qt item-model row signals (beginInsertRows etc.) if your host has no view model. Known source quirk to re-check when porting: in `editMarker`'s move-redo branch the re-added end snap uses `pos + previousDuration` (markerlistmodel.cpp:415-417 region) rather than the new duration — an apparent slip the tests do not currently pin; do not copy it blindly. Direct tests READ not executed (standing CTest block).
