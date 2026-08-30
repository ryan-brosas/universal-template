<!-- capsule-v2 -->
# Paste track-lane election — how do you map copied clips onto a DIFFERENT track layout, preserving above/below lane counts and audio-mirror pairing, when the destination has fewer lanes?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter's paste must decide, for every SOURCE track, which DESTINATION track receives its clips — when the destination layout differs, when audio clips are mirrored to video tracks, and when there simply are not enough lanes.

## getUsedTracks census → findPerfectTracks lane election → masterOffset tracksMap → mirror resolution
**Path/Symbol:** `src/timeline2/model/timelinefunctions.cpp:TimelineFunctions::getUsedTracks` (1969–2027), `pasteClips` core census+election (2080–2212) incl. `findPerfectTracks` lambda (2103–2136); mirror lookup `TimelineModel::getMirrorAudioTrackId` (`timelinemodel.cpp:751+`).
**Signature:** `bool getUsedTracks(const QDomNodeList &clips, const QDomNodeList &compositions, int sourceMasterTrack, int &topAudioMirror, TimelineTracksInfo &allTracks, QList<int> &singleAudioTracks, std::unordered_map<int,int> &audioMirrors)`; `findPerfectTracks(int &sourceTrackId, const QList<int> &sourceTracks, int &targetTrackId, const QList<int> &targetTracks)` (local lambda).
**Data Shape:** `TimelineTracksInfo` = `{videoIds, audioIds}` (track ids ordered by position); `audioMirrors` = source audio track → source video mirror; `singleAudioTracks` = audio tracks with NO mirror; `topAudioMirror` = highest mirrored video track; output `tracksMap` = source track id → destination track id (module static, per-paste scratch).

### Decisive source
```cpp
// timelinefunctions.cpp:1985-2003 — the census: audio clips carry audioTrack + optional mirrorTrack attributes
bool audioTrack = clipProducer.hasAttribute(QStringLiteral("audioTrack"));
if (audioTrack) {
    if (!allTracks.audioIds.contains(trackPos)) allTracks.audioIds << trackPos;
    int videoMirror = clipProducer.attribute(QStringLiteral("mirrorTrack")).toInt();
    if (videoMirror == -1 || sourceMasterTrack == -1) {
        if (!singleAudioTracks.contains(trackPos)) singleAudioTracks << trackPos;
        continue;                                   // unmirrored audio lane
    }
    audioMirrors[trackPos] = videoMirror;
    if (videoMirror > topAudioMirror) topAudioMirror = videoMirror;
    if (!allTracks.videoIds.contains(videoMirror)) allTracks.videoIds << videoMirror;
}
```
```cpp
// timelinefunctions.cpp:2103-2136 — lane election: preserve the above/below lane counts around the master
const int neededTracksBelow = sourceTrackId - sourceTracks.first();
const int neededTracksAbove = sourceTracks.last() - sourceTrackId;
const int existingTracksBelow = targetTracks.indexOf(targetTrackId);
const int existingTracksAbove = targetTracks.size() - (targetTracks.indexOf(targetTrackId) + 1);
...
if (existingTracksBelow < neededTracksBelow) {
    targetTrackId = targetTracks.at(qMin(neededTracksBelow, targetTracks.length() - 1));   // shift UP
    return;
}
if (existingTracksAbove < neededTracksAbove) {
    targetTrackId = targetTracks.at(qMax(0, targetTracks.size() - neededTracksAbove - 1)); // shift DOWN
    return;
}
if (!targetTracks.contains(targetTrackId)) targetTrackId = targetTracks.last();
```
```cpp
// timelinefunctions.cpp:2146-2157 — mirror-capacity check: enough mirrored video lanes at the elected spot?
int topAudioOffset = sourceTracks.videoIds.indexOf(topAudioMirror) - sourceTracks.videoIds.indexOf(sourceMasterTrack);
if (requestedAudioTracks > 0 && timelineTracks.audioIds.size() <= (timelineTracks.videoIds.indexOf(trackId) + topAudioOffset)) {
    int updatedPos = sourceTracks.audioIds.size() - topAudioOffset - 1;
    if (updatedPos < 0 || updatedPos >= timelineTracks.videoIds.size()) {
        pCore->displayMessage(i18n("Not enough tracks to paste clipboard"), ErrorMessage, 500);
        semaphore.release(1);
        return false;                               // hard refusal, transaction never starts
    }
    trackId = timelineTracks.videoIds.at(updatedPos);   // re-elect the master lane
}
```
```cpp
// timelinefunctions.cpp:2168-2195 — fill tracksMap: masterOffset for video, mirrors resolved pairwise
int masterOffset = targetMasterIx - sourceMasterTrack;
for (int tk : std::as_const(sourceTracks.videoIds)) {
    int newPos = qMax(0, masterOffset + tk);
    if (newPos >= timelineTracks.videoIds.size()) { ... return false; }
    tracksMap.insert(tk, timelineTracks.videoIds.at(newPos));
}
for (const auto &mirror : audioMirrors) {
    int videoIx = tracksMap.value(mirror.second);
    int mirrorIx = timeline->getMirrorAudioTrackId(videoIx);   // destination's OWN mirror pairing
    if (mirrorIx > 0) {
        tracksMap.insert(mirror.first, mirrorIx);
        if (!audioOffsetCalculated) {
            audioOffset = timeline->getTrackPosition(tracksMap.value(mirror.first)) - mirror.first;
            audioOffsetCalculated = true;
        }
    }
}
```

**Flow:** (1) CENSUS: walk clipboard `<clip>` and `<composition>` elements; audio clips declare `audioTrack` plus an optional `mirrorTrack`; unmirrored audio lanes go to `singleAudioTracks`, mirrored ones into `audioMirrors` and bump `topAudioMirror`; compositions contribute their b_track AND a_track to the video set; (2) SPAN CHECK: requested lanes = last − first + 1 per kind; more needed than exist ⇒ refuse before touching the model; (3) MASTER ELECTION: `findPerfectTracks` elects the destination master lane such that the number of lanes BELOW and ABOVE the master matches the source layout, shifting the target up or down when the destination is smaller; (4) MIRROR CAPACITY: if the elected master leaves too few mirrored video lanes for the audio mirrors, re-elect a lower master; impossible ⇒ refuse; (5) FILL: video lanes map by `masterOffset` (clamped at 0); audio mirrors resolve through the DESTINATION's own `getMirrorAudioTrackId` pairing (not the source's offsets); remaining single audio lanes map by a derived `audioOffset`; every overflow is a hard refusal with the semaphore released; (6) the resulting `tracksMap` is consumed by the re-insertion loop and by `GroupsModel::fromJsonWithOffset` for the group rebuild.
**Invariant:** the election preserves RELATIVE lane layout (above/below counts), never absolute track numbers; audio-mirror pairing is re-derived from the destination's mirror table, so AV-linked clips stay linked even when lane numbering differs; every insufficient-lane condition is a refusal BEFORE any mutation (the semaphore-guarded transaction never half-starts); `tracksMap` covers every source lane referenced by clips, compositions, and the group JSON — a missing entry would strand a leaf.
**Probe:** `tests/trimmingtest.cpp:968-1321` "Copy/paste" [CP]: cross-track paste works; "Paste when tracks get deleted" — deleting ALL audio tracks makes paste impossible (REQUIRE_FALSE) and undoing one deletion lets paste succeed on the surviving audio track (the span check + refusal path pinned end-to-end). The fps-ratio scaling that rides the same election has NO dedicated test section — evidence gap recorded.

## Get live surrounding code
**Retrieve:**
```bash
$ grep -n 'findPerfectTracks\|topAudioMirror\|audioMirrors\|singleAudioTracks' src/timeline2/model/timelinefunctions.cpp | head -14
1969:bool TimelineFunctions::getUsedTracks(const QDomNodeList &clips, const QDomNodeList &compositions, int sourceMasterTrack, int &topAudioMirror, TimelineTracksInfo &allTracks, QList<int> &singleAudioTracks, std::unordered_map<int, int> &audioMirrors)
1989:                if (!singleAudioTracks.contains(trackPos)) {
1995:            audioMirrors[trackPos] = videoMirror;
1996:            if (videoMirror > topAudioMirror) {
2074:    std::unordered_map<int, int> audioMirrors;
2080:    if(!getUsedTracks(clips, compositions, sourceMasterTrack, topAudioMirror, sourceTracks, singleAudioTracks, audioMirrors)) {
2103:    auto findPerfectTracks = [](int &sourceTrackId, const QList<int> &sourceTracks, int &targetTrackId, const QList<int> &targetTracks) {
2143:        findPerfectTracks(sourceMasterTrack, sourceTracks.videoIds, trackId, timelineTracks.videoIds);
2146:        int topAudioOffset = sourceTracks.videoIds.indexOf(topAudioMirror) - sourceTracks.videoIds.indexOf(sourceMasterTrack);
# executed live this pass; graph search_graph unavailable (MCP not connected in session)
```

## Verdict
Adopt the election order: census → span check → master election by above/below counts → mirror-capacity re-election → offset-based fill, all BEFORE any mutation. Adopt "resolve audio mirrors through the destination's own pairing table" — copying source offsets breaks AV links whenever layouts differ. Adopt hard refusal with released guard on any lane overflow. Adapt the XML attributes (audioTrack/mirrorTrack) to your clipboard schema; adapt `findPerfectTracks`'s clamp arithmetic if your lanes are unordered. Omit the composition a_track census if your host has no overlay items. Porting risk: the mirror-capacity re-election only shifts the master DOWN once — a pathological layout (mirrors needed above a full top) can still refuse where a smarter election would succeed; add a fixture for multi-mirror pastes before relying on it.
