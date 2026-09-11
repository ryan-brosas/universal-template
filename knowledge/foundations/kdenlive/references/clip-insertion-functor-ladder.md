<!-- capsule-v2 -->
# Clip-insertion functor ladder — how does a track validator answer "can this clip go here?" by returning the operation itself?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive`. **Question:** A porter must validate a drop position against blanks, collisions, mix partners and locks, and then perform MLT playlist surgery — without duplicating the validation logic between check-time and do-time.

## Validation-by-functor: append, fit-in-blank, or always-false
**Path/Symbol:** `src/timeline2/model/trackmodel.cpp:TrackModel::requestClipInsertion_lambda` (176–303) + `TrackModel::requestClipInsertion` (305–351).
**Signature:** `Fun requestClipInsertion_lambda(int clipId, int position, bool updateView, bool finalMove, bool groupMove, const QList<int> &allowedClipMixes)` · `bool requestClipInsertion(..., Fun &undo, Fun &redo, bool groupMove, bool newInsertion, const QList<int> &allowedClipMixes, bool bypassLock)`.
**Data Shape:** The lambda factory returns one of three functor shapes: (1) append-after-end when `target_clip >= count && is_blank_at(position)`; (2) fit-inside-blank when `blank_end >= position + length`; (3) `[](){ return false; }` sentinel on any rejection. `allowedClipMixes` whitelists co-moving mix partners whose overlap is legal.

### Decisive source
```cpp
if (!finalMove && !hasMix(clipId)) {
    if (allowedClipMixes.isEmpty()) {
        if (!m_playlists[0].is_blank_at(position) || !m_playlists[1].is_blank_at(position)) {
            qWarning() << "clip insert failed - non blank 1";
            return []() { return false; };                 // rejection IS a functor
        }
    } else {
        if (!m_playlists[target_playlist].is_blank_at(position))
            return []() { return false; };
        std::unordered_set<int> collisions = getClipsInRange(position, position + length);
        for (int c : collisions)
            if (!allowedClipMixes.contains(c)) return []() { return false; };
    }
}
...
return [this, position, clipId, end_function, ...]() {
    std::unique_ptr<Mlt::Field> field(m_track->field());
    field->block();                                        // lock MLT sandwich
    m_playlists[target_playlist].lock();
    ...
    int index = m_playlists[target_playlist].insert_at(position, *clip, 1);
    m_playlists[target_playlist].consolidate_blanks();
    m_playlists[target_playlist].unlock();
    field->unblock();
    ...
};
```

**Flow:** outer gate checks lock (`isLocked`, escape via bypassLock), negative position, A/V capability (`canBeAudio/canBeVideo`), coerces clip state with its own undo pair → lambda factory selects insertion shape → executing the chosen functor: block MLT field+playlist → set current track id → insert producer → consolidate blanks → unlock → `end_function` bookkeeping: store clip ptr in model map, set position, ADD BOTH EDGES as snap points (`m_snaps->addPoint(new_in/new_out)`), beginInsertRows/endInsertRows, monitor refresh + zone invalidation on finalMove → caller composes reverse (deletion lambda) via UPDATE_UNDO_REDO; on false runs `local_undo()` + assert.
**Invariant:** Check-time and do-time are the same code path — the validator cannot disagree with the executor; both A/V playlists must be blank for a preview insert unless partners are whitelisted; every committed insert registers exactly two snap points.
**Probe:** `tests/trimmingtest.cpp:146-150` pins adjacent resize/insert arithmetic (`requestItemResize(...) == -1` beyond blank, `== l` into freed space); `tests/modeltest.cpp` insertion suites assert `checkConsistency()` after each insert.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "kdenlive", query: "requestClipInsertion allowRequest validate", limit: 20 });
// executed live (name_pattern ^request.*): TrackModel::requestClipInsertion_lambda trackmodel.cpp:176-303;
// TrackModel::requestClipInsertion :305-351; TimelineModel::requestClipInsertion timelinemodel.cpp:2058-2496
```

## Verdict
Adopt validation-by-functor selection and the lock-sandwich ordering (field before playlist). Adapt blank bookkeeping to your storage (consolidate_blanks is MLT-specific), and replace `getClipsInRange` with your own interval index. Omit sub-playlist (`getSubPlaylistIndex`) nuance unless you port mixes too.
