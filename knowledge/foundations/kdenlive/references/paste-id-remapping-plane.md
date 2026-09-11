<!-- capsule-v2 -->
# Paste id-remapping plane — how do you paste a copied scene so every clip gets a NEW id while groups, mixes, compositions, subtitles, and track layout are all reconstructed correctly, including cross-document paste where bin ids collide?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter's copy/paste must re-materialize an entire scene under fresh ids at a new track/position, preserving group structure, same-track mixes, composition track offsets, subtitle events, effects, timeremap curves, and sub-playlist indices — and it must also work across documents where the copied bin ids may already be taken.

## copyClips scene document + tracksMap election + correspondingIds table + post-insertion reconstruction ladder
**Path/Symbol:** `src/timeline2/model/timelinefunctions.cpp:TimelineFunctions::copyClips` (1795–1955), `pasteClips` core (2041–2585) incl. `findPerfectTracks` lambda (2097–2125), `useFreeBinId` lambda (2312–2320), nested-sequence import (~2450–2560), `pasteTimelineClips` core (2595–2890); module statics `waitingBinIds`/`mappedIds`/`sequencesToInit`/`tracksMap` + `QSemaphore semaphore(1)` at :70–77; group rebuild via `GroupsModel::fromJsonWithOffset` (groupsmodel.cpp:926).
**Signature:** `static QString copyClips(const std::shared_ptr<TimelineItemModel> &timeline, const std::unordered_set<int> &itemIds, int mainClip)`; `static bool pasteClips(const std::shared_ptr<TimelineItemModel> &timeline, const QString &pasteString, int trackId, int position, Fun &undo, Fun &redo, int inPos = 0, int duration = -1, bool select = false)`; `static bool pasteTimelineClips(const std::shared_ptr<TimelineItemModel> &timeline, QDomDocument copiedItems, int position, Fun &undo, Fun &redo, bool pushToStack, int inPos, int duration, bool select)`.
**Data Shape:** clipboard = one `<kdenlive-scene>` XML document with attributes `fps`, `offset` (min start frame of the copy), `duration`, `masterTrack`/`masterAudioTrack` (track POSITION of the reference lane), `documentid`, `audioTracks`/`videoTracks`, plus `<clip>`/`<composition>`/`<subtitle>` children (each clip carrying its own `<mix>` child when it has a start mix), a `<bin>` subtree with the producers, and a `<groups>` text node (`GroupsModel::toJson(groupRoots)`, omitted in single-selection mode).

### Decisive source
```cpp
// timelinefunctions.cpp:2041-2058 — concurrency guard + document gate
if (!semaphore.tryAcquire(1)) {
    pCore->displayMessage(i18n("Another paste operation is in progress"), ErrorMessage, 500);
    while (!semaphore.tryAcquire(1)) { qApp->processEvents(); }   // module-static QSemaphore(1): one paste at a time
}
...
if (copiedItems.documentElement().tagName() != QLatin1String("kdenlive-scene")) {
    semaphore.release(1);
    return false;                                                  // foreign clipboard content refused up front
}
```
```cpp
// timelinefunctions.cpp:2097-2125 — findPerfectTracks: keep the relative lane layout when the target has fewer lanes
const int neededTracksBelow = sourceTrackId - sourceTracks.first();
const int neededTracksAbove = sourceTracks.last() - sourceTrackId;
...
if (existingTracksBelow < neededTracksBelow) {
    targetTrackId = targetTracks.at(qMin(neededTracksBelow, targetTracks.length() - 1));   // shift UP
} else if (existingTracksAbove < neededTracksAbove) {
    targetTrackId = targetTracks.at(qMax(0, targetTracks.size() - neededTracksAbove - 1)); // shift DOWN
}
```
```cpp
// timelinefunctions.cpp:2312-2320 — cross-document bin-id collision: remap to a free id, remember the mapping
auto useFreeBinId = [](QDomElement &producer, const QString &clipId, QMap<QString, QString> &mappedIds) {
    if (!pCore->projectItemModel()->isIdFree(clipId)) {
        QString updatedId = QString::number(pCore->projectItemModel()->getFreeClipId());
        Xml::setXmlProperty(producer, QStringLiteral("kdenlive:id"), updatedId);
        mappedIds.insert(clipId, updatedId);                       // old bin id → new bin id
        return updatedId;
    }
    return clipId;
};
```
```cpp
// timelinefunctions.cpp:2604-2717 — the heart: correspondingIds built DURING re-insertion
std::unordered_map<int, int> correspondingIds;
double ratio = 1.0;
if (copiedItems.documentElement().hasAttribute(QStringLiteral("fps-ratio"))) {
    ratio = copiedItems.documentElement().attribute(QStringLiteral("fps-ratio")).toDouble();
    offset *= ratio;                                               // fps change scales geometry AND offset
}
...
int newId;
bool created = timeline->requestClipCreation(originalId, newId, state, audioStream, speed, warp_pitch, timeline_undo, timeline_redo);
...
pastedItems.insert(newId);
correspondingIds[targetId] = newId;                                // OLD item id → NEW item id
...
res = res && timeline->getTrackById(curTrackId)->requestClipInsertion(newId, position + pos, true, true, timeline_undo, timeline_redo);
```
```cpp
// timelinefunctions.cpp:2757-2782 — mixes reconstructed AFTER every clip exists (see mix-persistence-loadmix-recovery)
if (correspondingIds.count(originalFirstClipId) > 0 && correspondingIds.count(originalSecondClipId) > 0) {
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
// timelinefunctions.cpp:2862-2884 — groups rebuilt from the serialized forest through the SAME id table + track map
const QString groupsData = copiedItems.documentElement().firstChildElement(QStringLiteral("groups")).text();
if (!groupsData.isEmpty()) {
    timeline->m_groups->fromJsonWithOffset(groupsData, tracksMap, position - offset, ratio, timeline_undo, timeline_redo);
}
Fun unselect = [timeline]() { timeline->requestClearSelection(); return true; };
PUSH_FRONT_LAMBDA(unselect, timeline_undo);                        // selection cleared on undo AND redo, not just now
PUSH_FRONT_LAMBDA(unselect, timeline_redo);
pCore->pushUndo(timeline_undo, timeline_redo, i18n("Paste timeline clips"));
semaphore.release(1);
```

**Flow:** (1) COPY: expand the selection to full group scope (unless single-selection mode), pick a non-subtitle main item as the reference, serialize each item's XML (clips attach their `<mix>` child when they have a start mix), embed the bin producers (expanding sequences to all their member bins), record `offset` = min start frame and `masterTrack` = the reference lane's POSITION (not id), and append the group forest as JSON of the involved roots only; (2) PASTE prelude: acquire the module-static semaphore (one paste at a time, statics `mappedIds`/`tracksMap` are per-paste scratch), refuse non-`kdenlive-scene` content, derive the source track set from the XML, then elect the destination master lane with `findPerfectTracks` (preserve the above/below lane counts, shifting the target when the destination has fewer lanes) and build `tracksMap` source-track-id → target-track-id, resolving audio mirrors through `getMirrorAudioTrackId`; (3) cross-document: for every embedded producer whose bin id is taken, `useFreeBinId` mints a free id and records old→new in `mappedIds`; nested sequences are imported bottom-up as xml-string producers with their ids remapped too; (4) re-insertion loop: for each `<clip>`, resolve its bin id through `mappedIds`, scale in/out/position by `fps-ratio`, clip to the requested [inPos, duration] window (adjusting newIn/newOut and cleaning the affected fade effects), coerce clip state to the target track type, create the NEW clip via `requestClipCreation`, re-apply timeremap links when the clip had one, restore endless-resize length, restore the sub-playlist index, import effects from XML, insert via the standard insertion functor ladder, and record `correspondingIds[oldId] = newId`; (5) post-insertion reconstruction, strictly AFTER all clips exist: mixes (id-remapped + ratio-scaled, see mix-persistence-loadmix-recovery), compositions (recreated with the a_track/b_track offset resolved against the target layout), subtitles (added through the SubtitleModel Fun variant), and finally the group forest via `fromJsonWithOffset(groupsData, tracksMap, position - offset, ratio)` which walks the serialized tree applying the id table and track map; (6) one undo entry is pushed, with an unselect lambda PREPENDED to both undo and redo so the selection state is restored consistently in both directions.
**Invariant:** secondary artifacts (mixes, groups, compositions) are NEVER reconstructed during the clip loop — only after every new id exists, keyed off the `correspondingIds` table; ids are minted by the same global counter (pass-1 plane), so pasted items are indistinguishable from native ones; the clipboard carries POSITIONS and offsets, never absolute target ids — the destination layout is resolved at paste time, which is why deleting source tracks after copy does not invalidate the clipboard; the whole operation is one semaphore-guarded, one-undo-entry transaction.
**Probe:** tests/trimmingtest.cpp:968–1321 "Copy/paste" [CP] (whole): invalid paste positions refused with state unchanged after each REQUIRE_FALSE; AVSplit pair pasted recreates the AVSplit group (getGroupElements == {cid3,cid4}, type asserted literally); selection set before paste does not leak into the result; "Paste when tracks get deleted": deleting the source clip keeps the clipboard valid, deleting ALL audio tracks makes paste impossible, undoing one deletion makes paste succeed on the surviving audio track. Deterministic probe below executed live.

## Get live surrounding code
**Retrieve:**
```bash
$ grep -n 'correspondingIds\|useFreeBinId\|tracksMap.insert' src/timeline2/model/timelinefunctions.cpp
2178:        tracksMap.insert(tk, timelineTracks.videoIds.at(newPos));
2186:            tracksMap.insert(mirror.first, mirrorIx);
2215:        tracksMap.insert(oldPos, timelineTracks.audioIds.at(offsetId));
2312:        auto useFreeBinId = [](QDomElement &producer, const QString &clipId, QMap<QString, QString> &mappedIds) {
2322:        auto pasteClip = [disableProxy, callBack, useFreeBinId, sourceFps, ratio](const QDomNodeList &clips, const QString &folderId, bool &clipsImported,
2391:                clipId = useFreeBinId(currentProd, clipId, mappedIds);
2454:                clipId = useFreeBinId(lastTractor, clipId, mappedIds);
2474:                        subClipId = useFreeBinId(tr, subClipId, mappedIds);
2604:    std::unordered_map<int, int> correspondingIds;
2717:        correspondingIds[targetId] = newId;
2763:        if (correspondingIds.count(originalFirstClipId) > 0 && correspondingIds.count(originalSecondClipId) > 0) {
2772:            mixData.firstClipId = correspondingIds[originalFirstClipId];
2773:            mixData.secondClipId = correspondingIds[originalSecondClipId];
# executed live this pass; graph search_graph unavailable (MCP not connected in session)
```

## Verdict
Adopt the two-phase reconstruction rule as the general pattern for any "duplicate a scene under new ids" problem: phase 1 creates the primary items and fills an old→new correspondence table; phase 2 resolves every secondary artifact (transitions, groups, overlays) against that table — never inline. Adopt the position-based clipboard (offset + master-lane position + fps-ratio, no absolute ids) so copies survive deletion of their sources and cross-document id collisions (mint-free-id + mapping table). Adopt the module-static semaphore for long multi-stage transactions that touch shared scratch state. Adapt the XML scene document to your host's clipboard format; omit the proxy-disable and sequence-expansion machinery unless your host has proxies/nested timelines. Porting risk: the fps-ratio path (ratio-scaled geometry + offset) has no dedicated test section — add a fixture pasting between different-fps documents before relying on it.
