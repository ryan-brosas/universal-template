<!-- capsule-v2 -->
# Mix persistence — how do you persist same-track mixes so they survive copy/paste and project load when only the MLT transition survives and original clip ids are gone?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter must make same-track mixes (see mix-plant-replant-ladder) durable: copy/paste must recreate them under NEW clip ids, and project load must re-attach a bare MLT transition to the right two clips when no id metadata survives in the playlist.

## Three createMix overloads + mixXml serialization + position-based loadMix recovery
**Path/Symbol:** `src/timeline2/model/trackmodel.cpp:TrackModel::createMix` overloads (2329–2381 full `MixInfo+params+tracks+finalMove`; 2383–2433 `MixInfo+isAudio`; 2435–2484 `clipIds+mixData`), `deleteMix` (2296–2327), `removeMix` (2506–2516), `setMixDuration`/`getMixDuration` (2486–2504), `mixXml` (2631–2660), `loadMix` (2662–2733), `getClipByPosition` (856–885); `src/timeline2/model/timelinemodel.cpp:TimelineModel::plantMix` (7864–7875); `src/timeline2/model/builders/meltBuilder.cpp:690` (project-load call site); `src/timeline2/model/timelinefunctions.cpp:1854` (copyClips → mixXml) and 2757–2782 (paste → createMix).
**Signature:** `bool createMix(MixInfo info, std::pair<QString, QVector<QPair<QString,QVariant>>> params, std::pair<int,int> tracks, bool finalMove)`; `bool createMix(MixInfo info, bool isAudio)`; `bool createMix(std::pair<int,int> clipIds, std::pair<int,int> mixData)`; `QDomElement mixXml(QDomDocument &document, int cid) const`; `bool loadMix(Mlt::Transition *t)`.
**Data Shape:** the `<mix>` element carries `firstClip`, `secondClip`, `firstClipPosition`, `asset`, `a_track`, `b_track`, `mixStart`, `mixEnd`, `mixOffset` plus `<param name value>` children; on project load the ONLY surviving artifact is the planted MLT transition with in/out frames and properties (`kdenlive_id`, `reverse`, `kdenlive:mixcut`).

### Decisive source
```cpp
// trackmodel.cpp:2329-2371 — full overload (paste/controller path): geometry comes from the caller
if (m_sameCompositions.count(info.secondClipId) > 0) { Q_ASSERT(false); return false; }   // one mix per second clip
int in = movedClip->getPosition();
int duration = info.firstClipInOut.second - info.secondClipInOut.first;
t->set_in_and_out(in, out);
t->set("kdenlive:mixcut", info.mixOffset);
t->set_tracks(tracks.first, tracks.second);
m_track->plant_transition(*t.get(), tracks.first, tracks.second);
... // params pasted into the asset XML <parameter> values
m_sameCompositions[info.secondClipId] = asset;      // BOTH registries written together,
m_mixList.insert(info.firstClipId, info.secondClipId);   // exactly as in build_mix
```
```cpp
// trackmodel.cpp:2631-2660 — serialization keys the mix by clip ids + live geometry
container.setAttribute("firstClip", m_mixList.key(cid));
container.setAttribute("secondClip", cid);
container.setAttribute("firstClipPosition", clip->getPosition());
container.setAttribute("asset", assetId);
for (const auto &p : params) { /* <param name=...>value</param> children */ }
std::pair<int,int> tracks = getMixTracks(cid);
container.setAttribute("a_track", tracks.first);
container.setAttribute("b_track", tracks.second);
std::pair<MixInfo,MixInfo> mixData = getMixInfo(cid);
container.setAttribute("mixStart", mixData.first.secondClipInOut.first);
container.setAttribute("mixEnd", mixData.first.firstClipInOut.second);
container.setAttribute("mixOffset", mixData.first.mixOffset);
```
```cpp
// timelinefunctions.cpp:2757-2782 — paste: old ids remapped through correspondingIds, geometry scaled by ratio
if (correspondingIds.count(originalFirstClipId) > 0 && correspondingIds.count(originalSecondClipId) > 0) {
    ...
    mixData.firstClipId = correspondingIds[originalFirstClipId];
    mixData.secondClipId = correspondingIds[originalSecondClipId];
    mixData.firstClipInOut.second = mix.attribute("mixEnd").toInt() * ratio;
    mixData.secondClipInOut.first = mix.attribute("mixStart").toInt() * ratio;
    mixData.mixOffset = mix.attribute("mixOffset").toInt() * ratio;
    std::pair<int,int> tracks = {mix.attribute("a_track").toInt(), mix.attribute("b_track").toInt()};
    if (tracks.first == tracks.second) { tracks = {0, 1}; }        // same-track mixes always span the sub-playlists
    timeline->getTrackById_const(mix.attribute("tid").toInt())->createMix(mixData, mixParams, tracks, true);
}
```
```cpp
// trackmodel.cpp:2662-2700 — load: clips are RE-DERIVED from positions, with a swap retry and an impossibility cut
int in = t->get_in();
int out = t->get_out() - 1;
bool reverse = t->get_int("reverse") == 1;
int cid1 = getClipByPosition(in, reverse ? 1 : 0);      // reverse-aware sub-playlist index
int cid2 = getClipByPosition(out, reverse ? 0 : 1);
if (cid1 < 0 || cid2 < 0) {
    cid1 = getClipByPosition(in, reverse ? 0 : 1);      // retry with swapped indices
    cid2 = getClipByPosition(out, reverse ? 1 : 0);
    if (cid1 < 0 || cid2 < 0) { field->lock(); field->disconnect_service(*t); field->unlock(); return false; }
} else {
    if (in == firstClipIn && in != m_allClips[cid2]->getPosition()) {
        if (m_allClips[cid1]->getPosition() > m_allClips[cid2]->getPosition()) { std::swap(cid1, cid2); }  // "SWAPPING CLIPS"
    }
    if (pos(cid1) > pos(cid2) || end(cid1) > end(cid2)) { disconnect_service(*t); return false; }   // impossible mix
}
int clipIn = m_allClips[cid2]->getPosition();
int clipOut = m_allClips[cid1]->getPosition() + m_allClips[cid1]->getPlaytime();
if (in != clipIn || out != clipOut) { t->set_in_and_out(clipIn, clipOut); }   // resync to LIVE positions
...
m_sameCompositions[cid2] = asset;
m_mixList.insert(cid1, cid2);
int mixCutPos = qMin(t->get_int("kdenlive:mixcut"), mixDuration);
setMixDuration(cid2, mixDuration, mixCutPos);
```

**Flow:** (1) creation always goes through one of three overloads that share the same tail: guard `m_sameCompositions.count(secondClipId)==0`, plant the transition, then write BOTH registries (`m_sameCompositions[second] = asset; m_mixList.insert(first, second)`) — the paired-registry invariant from mix-plant-replant-ladder holds for every entry point, not just requestClipMix; (2) copy serializes each mix of a copied clip via `mixXml` into the clipboard document (ids + live geometry + params + sub-playlist pair); paste remaps old→new ids through the `correspondingIds` table built while re-inserting clips, scales mixStart/mixEnd/mixOffset by the paste `ratio`, coerces a_track==b_track to {0,1}, and calls the full createMix overload with finalMove=true; (3) project load: meltBuilder plants every surviving transition and calls `plantMix(tid, t)`, which gates on `hasClipStart(t->get_in())` (the transition's in frame must land exactly on a clip start) before delegating to `loadMix`; loadMix re-derives the clip pair from POSITIONS alone — `getClipByPosition(pos, playlistIndex)` with the index chosen by the `reverse` flag, a swapped-index retry, a same-start "SWAPPING CLIPS" heuristic, and a hard disconnect for impossible ordering (first after second, or first's end past second's end); it then RESYNCS the transition's in/out to the live clip positions (the file may be stale), backfills asset parameters from the transition's own properties into the parameter model XML, clamps `kdenlive:mixcut` to the duration, and registers both registries.
**Invariant:** a mix exists iff BOTH registries agree (loadMix/createMix/deleteMix/removeMix are the only writers and all touch both); the transition's in/out is re-derived from live clip geometry at load time, never trusted from the file; `getClipByPosition` with playlist==-1 additionally resolves INTO the correct partner across a mix boundary using mix-cut offsets (856–885), so position lookups stay honest inside overlap zones; a mix whose clips cannot be found or ordered is DISCONNECTED from the field (under field lock) rather than left half-registered.
**Probe:** `tests/mixtest.cpp:162-234` (pass 2) pins registry integrity across create/delete/cut/resize round-trips; the persistence plane itself has no dedicated test file — loadMix recovery paths (swap retry, impossible-mix disconnect) are source-anchored only, recorded as evidence gap. Deterministic probe below executed live.

## Get live surrounding code
**Retrieve:**
```bash
$ grep -n 'loadMix\|mixXml\|plantMix' src/timeline2/model/trackmodel.cpp src/timeline2/model/timelinemodel.cpp
src/timeline2/model/trackmodel.cpp:2631:QDomElement TrackModel::mixXml(QDomDocument &document, int cid) const
src/timeline2/model/trackmodel.cpp:2662:bool TrackModel::loadMix(Mlt::Transition *t)
src/timeline2/model/timelinemodel.cpp:7864:bool TimelineModel::plantMix(int tid, Mlt::Transition *t)
src/timeline2/model/timelinemodel.cpp:7870:        return getTrackById_const(tid)->loadMix(t);
$ grep -n 'createMix(mixData, mixParams, tracks, true)' src/timeline2/model/timelinefunctions.cpp
2781:            timeline->getTrackById_const(mix.attribute(QLatin1String("tid")).toInt())->createMix(mixData, mixParams, tracks, true);
# executed live this pass; graph search_graph unavailable (MCP not connected in session)
```

## Verdict
Adopt the derive-don't-trust load strategy: persist the transition as the durable artifact, re-derive clip identity from positions at load time, and resync geometry to live state — it makes stale files self-healing. Adopt the layered recovery ladder (reverse-aware index → swapped-index retry → swap heuristic → impossible-order disconnect) as the template for any "re-attach an effect to moved operands" problem. Adopt the id-remapping-through-a-correspondence-table paste pattern (build old→new ids while re-inserting, resolve secondary artifacts afterwards). Keep the paired-registry write discipline at EVERY creation/deletion entry point. Adapt the QDomElement clipboard to your host's copy format; omit the parameter-backfill XML dance unless your host stores effect parameters separately from the effect instance. Porting risk: no repo test covers loadMix's swap/disconnect branches — add fixture tests with stale in/out and reversed flags before relying on them.
