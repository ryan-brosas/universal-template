<!-- capsule-v2 -->
# Same-track mix — how do you create a crossfade between two adjacent clips on ONE track without corrupting already-chained mixes further down the track?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter must add a same-track transition (mix) between clip A (first) and clip B (second) where the track physically holds TWO sub-playlists and later clips may already be chained in their own mixes.

## Delete → replant → build_mix → resize ladder with destroy_mix reverse
**Path/Symbol:** `src/timeline2/model/trackmodel.cpp:TrackModel::requestClipMix` (1865–2242); dual registries `m_mixList` (first→second) and `m_sameCompositions` (second→AssetParameterModel); `rearrange_playlists` functors (1920–2093); `build_mix` (2095–2150); `destroy_mix` (2152–2180).
**Signature:** `bool requestClipMix(const QString &mixId, std::pair<int,int> clipIds, std::pair<int,int> mixDurations, bool updateView, bool finalMove, Fun &undo, Fun &redo, bool groupMove)`.
**Data Shape:** per track: `m_playlists[0]` = main layer, `m_playlists[1]` = mix layer; a clip's `subPlaylistIndex` says which one it lives in; `mixPosition = qMax(firstPos, secondPos - mixDurations.second)` clamped by any existing start/end mix windows; `secondClipCut = maxPos - secondClipPos`; `remixPlaylists` flag set when the second clip's end-mix partner sits on the destination playlist.

### Decisive source
```cpp
// trackmodel.cpp:2182-2237 — the whole operation is delete + replay, reverse is the exact mirror
auto operation = requestClipDeletion_lambda(clipIds.second, updateView, finalMove, groupMove, false);
bool res = operation();
if (res) {
    Fun replay = [this, clipIds, dest_track, ...]() {
        ptr->getClipPtr(clipIds.second)->setSubPlaylistIndex(dest_track, m_id);
        bool result = rearrange_playlists();          // swap chained-mix partners' playlists + fix direction
        auto op = requestClipInsertion_lambda(clipIds.second, secondClipPos, updateView, finalMove, groupMove);
        result = result && op();
        if (result) {
            build_mix();                              // plant transition, register m_mixList/m_sameCompositions
            result = result && ptr->getClipPtr(clipIds.second)->requestResize(secondClipPos + secondClipDuration - mixPosition, false, ...);
            result = result && ptr->getClipPtr(clipIds.first)->requestResize(mixPosition + mixDurations.first + mixDurations.second - firstClipPos, true, ...);
        }
        return result;
    };
    Fun reverse = [this, clipIds, source_track, ..., destroy_mix, ...]() {
        destroy_mix();                                // disconnect transition, clear registries, setMixDuration(0)
        ptr->getClipPtr(clipIds.second)->requestResize(secondClipDuration, false, ...);
        ptr->getClipPtr(clipIds.first)->requestResize(firstClipDuration, true, ...);
        bool result = operation();                    // re-delete to restore original layout
        ptr->getClipPtr(clipIds.second)->setSubPlaylistIndex(source_track, m_id);
        result = result && rearrange_playlists_undo();
        auto op = requestClipInsertion_lambda(clipIds.second, secondClipPos, updateView, finalMove, groupMove);
        return result && op();
    };
    res = replay();
    if (res) { PUSH_LAMBDA(replay, operation); UPDATE_UNDO_REDO(operation, reverse, undo, redo); }
    else { reverse(); }                               // compensating rollback on ANY stage failure
}
```
```cpp
// trackmodel.cpp:2103-2142 — build_mix plants the transition between the two sub-playlists
if (isAudioTrack()) { t = TransitionsRepository::get()->getTransition("mix"); t->set("kdenlive:mixcut", secondClipCut); ... }
else { assetName = isLuma ? "dissolve" : (mixId.isEmpty() || isLuma || mixId=="mix" ? "luma" : mixId); }
t->set_in_and_out(mixPosition, mixPosition + mixDurations.first + mixDurations.second);
if (dest_track == 0) { t->set_tracks(1, 0); m_track->plant_transition(*t.get(), 1, 0); }   // REVERSED direction
else                 { t->set_tracks(0, 1); m_track->plant_transition(*t.get(), 0, 1); }
m_sameCompositions[clipIds.second] = asset;
m_mixList.insert(clipIds.first, clipIds.second);
```

**Flow:** (1) locked track refuses; (2) compute the mix window, clamped against the first clip's existing start mix and the second's existing end mix (`getMixInfo`), and detect whether downstream chained mixes must be remapped (`remixPlaylists`); (3) DELETE the second clip from its current playlist; (4) `replay`: move it to the destination sub-playlist, run `rearrange_playlists` (blank-out → move → replug each chained partner across playlists, then rebuild each affected transition with `updateCompositionDirection(reverse)` so its direction matches the new side), reinsert at the original position, `build_mix` (plant transition with `kdenlive:mixcut`, reversed tracks when dest_track==0), resize BOTH clips so they overlap exactly over the mix window; (5) undo = `destroy_mix` (disconnect service under field block, erase both registries, `setMixDuration(0)`) + restore both durations + re-run the deletion + restore source playlist + inverse rearrange + reinsert. Any failure mid-replay runs `reverse()` — the same ladder in mirror order.
**Invariant:** `m_mixList.size() == m_sameCompositions.size()` (asserted by `mixCount()`); a mix is keyed by its SECOND clip in `m_sameCompositions` and by its FIRST clip in `m_mixList` — both must be written/erased together; the transition's in/out always equals the current overlap of the two clips (see mix-info-sync-plane for the reconciliation that keeps this true after moves); direction is encoded as which sub-playlist pair the transition spans (0→1 normal, 1→0 reversed).
**Probe:** `tests/mixtest.cpp:162-175` create/delete round-trips state0↔state2 under undo/redo; `tests/mixtest.cpp:850-999` "Test chained mixes and check mix direction": four sequential mixes yield alternating `mixIsReversed` patterns (false / false,true / false,true,false / false,true,false,true) — inserting a new mix at the front flips the direction of every subsequent mix, and `switchComposition` to slide/wipe preserves the exact same direction map; the full undo chain returns to state0.

## Get live surrounding code
**Retrieve:**
```bash
$ grep -n 'build_mix\|destroy_mix\|rearrange_playlists =' src/timeline2/model/trackmodel.cpp
1920:    Fun rearrange_playlists = []() { return true; };
1938:        rearrange_playlists = [this, map = rearrangedPlaylists]() {
2095:    Fun build_mix = [clipIds, mixPosition, mixDurations, dest_track, secondClipCut, mixId, this]() {
2152:    Fun destroy_mix = [clipIds, this]() {
2185:        Fun replay = [this, clipIds, dest_track, ...]() {
2194:                build_mix();
2212:        Fun reverse = [this, clipIds, source_track, ..., destroy_mix, ...]() {
2214:            destroy_mix();
# executed live this pass; graph search_graph unavailable (MCP not connected in session)
```

## Verdict
Adopt the dual-sub-playlist representation and the delete→replant→build→resize ladder with its mirrored reverse — it is the only shape that keeps chained mixes consistent because every stage is itself an undoable primitive. Adopt the paired-registry discipline (first-keyed list + second-keyed asset map, erased together). Adapt the MLT `plant_transition`/field-block calls to your host's compositor; omit the luma/dissolve asset selection unless you port transition assets. The `rearrange_playlists` blank-out/move/replug/direction-fix sequence is the reusable kernel for "insert a boundary into the middle of a chain of pairwise transitions".
