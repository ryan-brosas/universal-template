<!-- capsule-v2 -->
# Melt-load repair ladder — how do you rebuild a whole document from a serialized render graph through the same validated mutation API used by interactive edits, repairing corruption instead of aborting?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter must load a project file whose serialized form is the RENDER graph (MLT tractor), not the document model — clip ids may be stale, bin references broken, compositions mis-targeted — and must produce a consistent model plus an honest user-facing repair report, or a clean failure.

## constructTimelineFromMelt + binIdCorresp remap + fail-soft per-item repair
**Path/Symbol:** `src/timeline2/model/builders/meltBuilder.cpp:constructTimelineFromMelt` (350–633), `constructTrackFromMelt` playlist overload (757–1046), module statics `binIdCorresp`/`m_errorMessage`/`m_notesLog`/`brokenBinProducers` (31–36); call site `src/project/projectmanager.cpp:2186` region; consumer of `TimelineModel::requestTrackInsertion`, `requestCompositionInsertion` (6235–6284), `requestClipMove`, `requestItemDeletion`.
**Signature:** `bool constructTimelineFromMelt(const std::shared_ptr<TimelineItemModel> &timeline, Mlt::Tractor tractor, const QString &originalDecimalPoint, const QString &chunks, const QString &dirty, bool enablePreview, bool *projectErrors)`; `bool constructTrackFromMelt(..., Mlt::Playlist &track, Fun &undo, Fun &redo, bool audioTrack, const QString &originalDecimalPoint, int playlist, const QList<Mlt::Transition *> &compositions)`.
**Data Shape:** `binIdCorresp: std::unordered_map<QString,QString>` maps serialized bin control-uuid → live bin id (cleared at :50 and :106, filled by `loadBinPlaylist`); per-item repair output accumulates in `m_notesLog` (clickable timeline links) + `m_errorMessage` (dialog lines); `MLT_TESTS` env suppresses the user-facing warning path (honored by tests via TestMain.cpp:67).

### Decisive source
```cpp
// meltBuilder.cpp:350-361 — the load runs through the SAME Fun accumulators and
// requestReset as any interactive session; nothing mutates the model directly.
bool constructTimelineFromMelt(const std::shared_ptr<TimelineItemModel> &timeline, Mlt::Tractor tractor, ...)
{
    if (tractor.count() == 0) { return false; }
    Fun undo = []() { return true; };
    Fun redo = []() { return true; };
    // First, we destruct the previous tracks
    timeline->requestReset(undo, redo);
```
```cpp
// meltBuilder.cpp:757-770 + 855-870 — per playlist entry: blank skipped; processed bin clips
// take kdenlive:id as-is; unknown control_uuid ⇒ recover by resource URL or drop WITH a note.
for (int i = 0; i < max; i++) {
    if (track.is_blank(i)) { continue; }
    std::shared_ptr<Mlt::Producer> clip(track.get_clip(i));
    int position = track.clip_start(i);
    ...
    if (clip->parent().get_int("_kdenlive_processed") == 1) {
        binId = QString(clip->parent().get("kdenlive:id"));
    } else {
        const QString clipId = clip->parent().get("kdenlive:control_uuid");
        if (QUuid(clipId).isNull()) { ...notesLog << "...found and removed..."; continue; }
```

**Flow:** requestReset → reserved-name skip (`playlistmain`, `timeline_preview`, `black_track`, …) → A/V track census pass → per track: `requestTrackInsertion` + `constructTrackFromMelt` (locked tracks collected, applied LAST via `lockTrack`) → composition harvest from the tractor service chain (skips `internal_added` and `kdenlive:mixcut` transitions — those are mixes and internal track compositing, not user compositions) → per composition: invalid-track-reference removal with notes, automatic-composition `force_track` promotion when it targets the wrong lower track, `requestCompositionInsertion` with source properties → `buildTrackCompositing` → locked state → `isLoading=false`. Per clip inside `constructTrackFromMelt`: `_kdenlive_processed` fast path; control-uuid → `binIdCorresp` map; self-embedding sequence refusal (binId == sequenceBinId ⇒ drop with note); producer-type mismatch ⇒ reset + recheck with typed `fixStatus`; playlist>0 clips verify their mix partners exist on playlist 0 — missing mix ⇒ resize-to-fit and demote to playlist 0, or drop; `enforceTopPlaylist` repair when a clip sits on a sub-playlist without a mix; `moveStatus != MoveSuccess` ⇒ `requestItemDeletion` + typed error message.
**Invariant:** the model is never left inconsistent by a bad item — every repair path either fixes the item through ordinary request* calls (which validate and roll back internally) or removes it and records a note; a failed track load aborts the whole load (`ok` latch ⇒ return false) AFTER per-item repairs, and the user always gets the notes log. Load order matters: clips before compositions before internal track compositing; locks last.
**Probe:** NO direct test file covers the builder (`grep -rln constructTimelineFromMelt tests/` = 0 files) — recorded evidence gap; behavior is anchored by the request* API tests it drives (compositiontest.cpp, markertest.cpp read this pass; modeltest/movetest/trimmingtest passes 1–4) and by `MLT_TESTS=1` in TestMain.cpp:67 proving the test harness exercises this path with warnings suppressed.

## Get live surrounding code
**Retrieve:**
```
grep -n "constructTrackFromMelt\|binIdCorresp\|kdenlive:playlistid" src/timeline2/model/builders/meltBuilder.cpp
```
Executed byte-for-byte (pass 5, pin 62d6b0b79c51): hits at 33, 36, 38, 50, 54, 66, 67, 77, 78, 106, 107, 109 (+ later body sites) — the id-correspondence table and its clear/fill lifecycle confirmed at the cited lines.
```
grep -n "replantCompositions\|unplantComposition" src/timeline2/model/timelinemodel.cpp
```
Executed byte-for-byte: 2791, 2807, 6565, 6572, 6600, 6603, 6627, 6641, 6709 — the composition plant/unplant machinery the builder drives via requestCompositionInsertion.

## Verdict
Adopt the discipline of rebuilding a document from a serialized render graph exclusively through the interactive mutation API on one undo pair, the id-correspondence table for stale references, and the fail-soft per-item repair ladder with an honest user-facing report. Adapt the repair policies (recover-by-resource, resize-to-fit, force_track promotion) to your host's corruption model. Omit MLT tractor/field traversal and the KDE i18n/notes-log plumbing. Evidence caveat: builder itself has NO direct test file — cite as source-anchored; the `editMarker` move-redo snap quirk noted in guide-marker-snap-registry-plane is a separate known slip. Direct tests READ not executed (standing CTest block).
