<!-- capsule-v2 -->
# Composition lifecycle — how do you model overlay items that are NOT playlist entries, validated by interval scan, planted into a render graph where planting order is semantically load-bearing, and moved with an automatic duration refit?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter must add overlay/transition items to a track model where the item does not occupy the playlist, must never overlap a sibling on the same track, and whose render-graph planting order (a_track/b_track) changes meaning when it moves.

## Composition insertion/deletion lambdas + interval-scan validation + ordered field replant
**Path/Symbol:** `src/timeline2/model/trackmodel.cpp:TrackModel::requestCompositionInsertion` (1434–1447), `requestCompositionDeletion` (1449–1467), `requestCompositionDeletion_lambda` (1469–1519), `requestCompositionInsertion_lambda` (1521–1559), `hasIntersectingComposition` (1561–1577); `src/timeline2/model/timelinemodel.cpp:TimelineModel::requestCompositionMove` public (6430–6470) + core (6525–6625), `replantCompositions` (6627–6707), `unplantComposition` (6709+), creation entries (6235–6284); `src/timeline2/model/compositionmodel.cpp:CompositionModel::construct` (25–71), `requestResize` (72–203).
**Signature:** `bool requestCompositionInsertion(int compoId, int position, bool updateView, bool finalMove, Fun &undo, Fun &redo)`; `bool hasIntersectingComposition(int in, int out) const`; `bool requestCompositionMove(int compoId, int trackId, int compositionTrack, int position, bool updateView, bool finalMove, Fun &undo, Fun &redo)`; `bool replantCompositions(int currentCompo, bool updateView)`.
**Data Shape:** per-track `m_allCompositions` (id→CompositionModel) + `m_compoPos` (position→id) — a composition has NO playlist index; its geometry is (position, playtime) plus an MLT `a_track`/`b_track` pair. Planting order invariant: transitions must be planted with a_track decreasing and b_track increasing.

### Decisive source
```cpp
// trackmodel.cpp:1521-1536 — validation happens BEFORE the functor is even built:
// an intersecting target yields the always-false sentinel, mirroring clip insertion.
Fun TrackModel::requestCompositionInsertion_lambda(int compoId, int position, bool updateView, bool finalMove)
{
    QWriteLocker locker(&m_lock);
    bool intersecting = true;
    if (auto ptr = m_parent.lock()) {
        intersecting = hasIntersectingComposition(position, position + ptr->getCompositionPlaytime(compoId) - 1);
    }
    if (!intersecting) {
        return [compoId, this, position, updateView, finalMove]() { ... };
    }
    return []() { return false; };
}
```
```cpp
// timelinemodel.cpp:6627-6645 — any a_track change forces disconnect-ALL then replant in
// canonical order: compositions sorted by a_track DESC, b_track ASC, under a field lock.
bool TimelineModel::replantCompositions(int currentCompo, bool updateView)
{
    std::vector<std::pair<int, int>> compos;
    for (const auto &compo : m_allCompositions) {
        int trackId = compo.second->getCurrentTrackId();
        if (trackId == -1 || compo.second->getATrack() == -1) { continue; }
        int trackPos = getTrackMltIndex(trackId);
        compos.emplace_back(trackPos, compo.first);
        if (compo.first != currentCompo) { unplantComposition(compo.first); }
    }
    // sort by decreasing b_track (a_track DESC, then b_track ASC)
```

**Flow:** validate (interval scan) → mutation functor or false-sentinel → core move = unplant (old track) → track-level deletion lambda → track-level insertion lambda → setATrack + replant (new track) → any stage failure ⇒ `local_undo()` + `Q_ASSERT` → `UPDATE_UNDO_REDO` into caller accumulators. Public move adds: group fan-out via `requestGroupMove` when grouped; `allowResize` refits duration to `getOptimalTransitionDuration(trackId, position)` after the move; same-track moves degrade to a view-notify (`notifyViewOnly` + `update_model` StartRole lambda). Creation entries capture `deregisterComposition_lambda` as inverse BEFORE `CompositionModel::construct` and capture a `shared_ptr` in the redo functor — the same ownership pattern as track insertion.
**Invariant:** at most one composition per (track, position-interval) — enforced by `hasIntersectingComposition`'s `m_compoPos.lower_bound(in)` scan checking both the found successor and its predecessor's end; planting order (a_track desc, b_track asc) is never violated because any a_track mutation replants everything; composition edges are snap points (`m_snaps->addPoint(new_in/new_out)` in the insertion lambda, removed in the deletion lambda).
**Probe:** `tests/compositiontest.cpp` "Composition manipulation" (450L whole): overlapping same-track move refused BOTH directions (`REQUIRE_FALSE(requestCompositionMove(cid1, tid1, pos2 ± 2))`) with full state lambda re-asserted after every refusal; inserted resize blocked by a neighbor returns -1 in both directions even at a 0-frame gap; moving the blocker away re-enables growth; orphan resize is unconstrained.

## Get live surrounding code
**Retrieve:**
```
grep -n "requestCompositionInsertion_lambda\|requestCompositionDeletion_lambda\|hasIntersectingComposition" src/timeline2/model/trackmodel.cpp
```
Executed byte-for-byte (pass 5, pin 62d6b0b79c51): hits at 1413, 1440, 1442, 1460, 1462, 1469, 1521, 1526, 1561 — exactly the cited symbol family, no noise.
```
grep -n "replantCompositions\|unplantComposition" src/timeline2/model/timelinemodel.cpp
```
Executed byte-for-byte: hits at 2791, 2807, 6565, 6572, 6600, 6603, 6627, 6641, 6709 — replant/unplant sandwich confirmed at the cited core-move range.

## Verdict
Adopt the interval-scan validation + always-false-sentinel functor shape, the unplant→reinsert→replant move sandwich with per-stage rollback+assert, and the disconnect-all/replant-in-canonical-order rule whenever render-graph planting order is semantic. Adapt `m_compoPos` to your host's overlay index and `getOptimalTransitionDuration` to your auto-fit policy. Omit MLT `Mlt::Field` mechanics and the slide/wipe end-keyframe refresh special cases (compositionmodel.cpp:122-150) — host-renderer specific. Direct tests READ not executed (standing CTest block); composition resize slide/wipe keyframe branches are source-anchored only.
