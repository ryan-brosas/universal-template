<!-- capsule-v2 -->
# Bin-load id correspondence plane — how do you rebuild clip identity when a serialized project's bin ids must be re-keyed on load, with two load lanes (full bin playlist vs hash-matched tractor fallback) and a reopen lane that must NOT remap?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive`. **Question:** when a saved project is reopened, every serialized bin id is stale — how does the loader re-key clip identity without corrupting cross-references, and which of the three load lanes remaps and which must not?

## Bin-load twin + id-correspondence seam
**Path/Symbol:** `src/timeline2/model/builders/meltBuilder.cpp:constructTimelineFromTractor` (:90-349) + `src/bin/projectitemmodel.cpp:loadBinPlaylist` (:1383-1580) / `loadTractorPlaylist` (:1581-1693).
**Signature:** `bool constructTimelineFromTractor(const std::shared_ptr<TimelineItemModel> &timeline, const std::shared_ptr<ProjectItemModel> &projectModel, Mlt::Tractor tractor, const QString &originalDecimalPoint, const QString &chunks, const QString &dirty, bool enablePreview)`; `QMap<QUuid, QString> loadBinPlaylist(Mlt::Service *documentTractor, std::unordered_map<QString, QString> &binIdCorresp, QStringList &expandedFolders, QStringList &extraBins, const QUuid &activeUuid, int &zoomLevel)`.
**Data Shape:** `binIdCorresp` is a module-static `std::unordered_map<QString, QString>` (meltBuilder.cpp:33) keyed by serialized `kdenlive:control_uuid` (QUuid string) → fresh bin id string; cleared at every entry (`loadProjectBin` :50, `constructTimelineFromTractor` :106). `brokenSequences` maps QUuid → control_uuid for clips that could not be restored.

### Decisive source
```cpp
// meltBuilder.cpp:103-112 — the lane election
if (projectModel) {
    // This is an old format project file
    int zoomLevel = -1;
    if (timeline->uuid() == pCore->currentTimelineId()) {
        binIdCorresp.clear();
        projectModel->loadBinPlaylist(&tractor, binIdCorresp, expandedFolders, extraBins, timeline->uuid(), zoomLevel);
    } else {
        projectModel->loadTractorPlaylist(tractor, binIdCorresp);
    }
} else {
    // loading an extra timeline
    if (tractor.property_exists("_dontmapids")) {
        // We are reopening a closed sequence, don't use mapped ids!
        useMappedIds = false;
    }
}
```
```cpp
// projectitemmodel.cpp:1512-1531 — the re-keying loop (bin playlist lane)
while (!binProducers.isEmpty()) {
    ...
    QString newId = QString::number(getFreeClipId());
    QString parentId = qstrdup(prod->get("kdenlive:folderid"));
    if (parentId.isEmpty()) { parentId = QStringLiteral("-1"); }
    else {
        if (binIdCorresp.count(parentId.section(QLatin1Char('.'), -1)) == 0) {
            // Error, folder was lost
            parentId = QStringLiteral("-1");
        }
    }
    prod->set("_kdenlive_processed", 1);
    const QString uuid(prod->get("kdenlive:control_uuid"));
    requestAddBinClip(newId, prod, parentId, undo, redo);
    binIdCorresp[uuid] = newId;
}
```

**Flow:** (1) `requestReset` clears the timeline on throwaway undo/redo lambdas; (2) lane election: full project file with the bin model present → `loadBinPlaylist` (the bin playlist stored under `xml_retain` data key `binPlaylistId` is the document of record for clip identity); extra timeline without a bin model → `loadTractorPlaylist` (hash-matched fallback); reopening a closed sequence (`_dontmapids` property) → `useMappedIds = false`, ids are used as-is; (3) `loadBinPlaylist` walks the retained playlist: folders first (folder ids remapped through `binIdCorresp` so `sequenceFolder`/`audioCaptureFolder` pointers survive), then producers — id-less bin clips get a TEMPORARY NEGATIVE id (`id = -getFreeClipId()`) so they cannot collide with not-yet-loaded positive ids; duplicate sequence ids go to `brokenSequences` (reported via KMessageBox, not fatal); a missing active sequence is recovered from `tractor.track(0)`'s parent producer; (4) the real insertion loop re-keys EVERY producer to a fresh `getFreeClipId()` and fills `binIdCorresp[control_uuid] = newId`; (5) back in the builder, the tractor census skips reserved playlist names {playlistmain, timeline_preview, timeline_overlay, black_track, overlay_track}, counts A/V tracks (nested double-tracks count as audio when `kdenlive:audio_track==1`), then imports tracks in a second pass: `requestTrackInsertion(-1, tid, ...)` + `constructTrackFromMelt(...)` per track, trackTag `A{n}`/`V{n}` from running counters, locked-track indexes collected but applied LAST via `timeline->lockTrack(tid, true)`; (6) compositions harvested from the tractor producer (skip `internal_added` and `kdenlive:mixcut`; skip `b_track >= tractor.count()`; unknown `kdenlive_id` refused with an error note; automatic compositions (`force_track==0`) whose a_track is not the video track below are force-promoted with a note), inserted via `requestCompositionInsertion`, then `buildTrackCompositing()`; (7) on track-load failure `undo()` runs and the load returns false — but a failed composition only logs and continues.

**Invariant:** `binIdCorresp` is filled BEFORE any timeline clip consumes it (constructTrackFromMelt reads it at :792-847), and every consumer must tolerate the empty map (`binIdCorresp.size() == 0` falls back to raw `kdenlive:id`); the reopen lane (`_dontmapids`) must never remap because the sequence's own serialized ids are still live in the bin. Folder pointers are remapped through the same table, so a lost folder degrades to root (`-1`) rather than a dangling id.

**Probe:** no direct test file covers this plane (grep `constructTimelineFromTractor|loadBinPlaylist|loadTractorPlaylist` over tests/ = 0 files — evidence gap recorded). Executed deterministic probe:
```
grep -n "binIdCorresp" src/timeline2/model/builders/meltBuilder.cpp
```
→ 24 hits at lines 33, 50, 54, 66, 67, 77, 78, 106, 107, 109, 114, 115, 125, 126, 366, 371, 372, 382, 383, 792, 794, 795, 823, 847 (quoted from the run).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "kdenlive", query: "loadBinPlaylist binIdCorresp control_uuid rekey", limit: 10, fields: ["signature", "name", "file"] });
```
(Graph MCP was not connected in the authoring session; the grep probe above was executed byte-for-byte instead.)

## Verdict
Adopt the three-lane election with an explicit no-remap escape hatch, the control-uuid→fresh-id correspondence table filled during re-keying, temporary negative ids for id-less producers, and collect-then-apply-last lock state. Adapt the MLT xml_retain container and QUuid control-uuid keying to your serializer's identity tokens. Omit the KDE i18n/KMessageBox reporting and the qApp->processEvents() progress pumping (UI-coupled). State the caveat: this plane has no direct test coverage in the source repo; anchor any port with your own round-trip load tests.
