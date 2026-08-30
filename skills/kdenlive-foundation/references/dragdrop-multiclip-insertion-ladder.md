<!-- capsule-v2 -->
# Drag-drop multi-clip insertion ladder — how does a multi-stream bin drop become N validated insertions across auto-created audio tracks?

**Source:** kdenlive GPL-3.0 `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (MCP not connected this session — direct source+test read fallback). **Question:** How do you prompt the user exactly once for track creation, insert every stream of every dropped clip, and roll back all-or-nothing — while grouping the created mirror clips as AVSplit?

## requestMultipleClipsInsertion + clipAudioStreamInfo + promptAudioTrackCreation + ensureAudioTracksForClip
**Path/Symbol:** `src/timeline2/model/timelinefunctions.cpp:TimelineFunctions::requestMultipleClipsInsertion` (:114-149); `src/timeline2/model/timelinemodel.cpp:TimelineModel::clipAudioStreamInfo` (:599-666), `promptAudioTrackCreation` (:1963-2013), `requestClipInsertion` public (:2015-2055) + functor overload (:2061-2496), `ensureAudioTracksForClip` (:2498-2589).
**Signature:** `bool requestMultipleClipsInsertion(timeline, const QStringList &binIds, int trackId, int position, QList<int> &clipIds, bool logUndo, bool refreshView)`; `QVariantList clipAudioStreamInfo(const QString &binClipId, int trackId, bool createTracks, Fun &undo, Fun &redo)` (returns `{totalStreamCount, availableTracks, isEnoughTracks}`, or `{-1,-1,true}` on user cancel).
**Data Shape:** `binIds` entries carry the drop grammar `A2/10/50` (A/V prefix = forced audio/video-only drop, `/in/out` suffix = optional source range). `m_audioTarget: QMap<trackId, streamIndex>` maps destination audio tracks to clip stream indices; `allowedTracks` accumulates newly created tracks so later stages accept them.

### Decisive source
```cpp
// requestMultipleClipsInsertion — one prompt, one undo entry, all-or-nothing
if (logUndo) {
    QVariantList result = timeline->clipAudioStreamInfo(binIdsString, trackId, true, undo, redo);
    if(result[0].toInt() == -1) {
        undo();               // user cancelled track creation
        return false;
    }
}
for (const QString &binId : binIds) {
    if (timeline->requestClipInsertion(binId, trackId, position, clipId, logUndo, refreshView, false, undo, redo)) {
        clipIds.append(clipId);
        position += timeline->getItemPlaytime(clipId);
    } else {
        undo();               // any failure rolls back EVERYTHING inserted so far
        clipIds.clear();
        return false;
    }
}
if (logUndo) pCore->pushUndo(undo, redo, i18n("Insert Clips"));
```

```cpp
// ensureAudioTracksForClip — compositing bracket around track creation
clean_compositing();                       // removeTrackCompositing BEFORE any insertion
... requestTrackInsertion(insertPos, newTid, ...) ...
    m_audioTarget.insert(newTid, stream);  // stream-ordered: next to lowest already-mapped target
...
if (result) {
    rebuild_compositing();                 // buildTrackCompositing AFTER all insertions
    PUSH_FRONT_LAMBDA(clean_compositing, redo);  PUSH_FRONT_LAMBDA(clean_compositing, undo);
    PUSH_LAMBDA(rebuild_compositing, redo);      PUSH_LAMBDA(rebuild_compositing, undo);
} else {
    rebuild_compositing();                 // failure STILL rebuilds compositing
}
```

**Flow:** (1) Census + single prompt: `clipAudioStreamInfo` parses the semicolon-joined bin-id list, strips A/V prefixes, skips V-only entries, sums `totalStreamCount` and takes `maxStreamsPerClip`; `availableTracks = 1 + lower audio tracks` capped at `maxStreamsPerClip`; if short and `createTracks`, ONE `promptAudioTrackCreation` call (which computes `tracksToInsertBeforeMirror = lowerVideoTracks - audioTracks - 1` when the drop track has no mirror, asks via AutoTrackCreationDialog, and delegates to `ensureAudioTracksForClip`); cancel returns `{-1,-1,true}` and the caller undoes. (2) Per-clip insertion: `requestClipInsertion` elects drop type from the A/V prefix, refuses self-embedding sequences (`canBeDropped`), parses the in/out-suffix duration, then in the drag-drop lane fits streams to available tracks (`keys.mid(0, availableTracks)`), pre-checks availability/locks on the main track AND every lower track for multi-stream drops, creates the clip (`requestClipCreation`), moves it, then elects mirror/dropTargets and creates one clip per extra stream on `audio_undo`/`audio_redo` with Q_ASSERT rollback, finally grouping all created ids (`createdMirrors`, seeded with the main clip id) as `GroupType::AVSplit`. (3) The target-lane variant prompts only for streams missing an `m_audioTarget` assignment, assigns created tracks to the missing streams, and filters `keys` to assigned streams. (4) `ensureAudioTracksForClip` brackets ALL track insertions with compositing teardown/rebuild (the rebuild lambdas are pushed so undo/redo replay the bracket), inserts stream-targeted tracks next to the lowest already-mapped target, and rebuilds compositing even on failure.
**Invariant:** Exactly ONE user prompt per drop operation; every created track joins `allowedTracks` so downstream stages accept it; any per-clip failure rolls back the whole multi-clip insertion through the shared accumulators; the AVSplit group always contains the main clip plus every successfully created mirror; compositing is never left torn down, even on failure.
**Probe:** `grep -n "requestMultipleClipsInsertion" src/timeline2/model/timelinefunctions.cpp src/timeline2/model/timelinefunctions.hpp` → 2 hits (definition :114, header declaration). Executed this session. Evidence gap: NO test file references requestMultipleClipsInsertion, clipAudioStreamInfo, promptAudioTrackCreation, or ensureAudioTracksForClip (grep over tests/ = 0 files) — the whole ladder is integration-only.

## Get live surrounding code
**Retrieve (graph MCP unavailable; executed deterministic grep substitute):**
```bash
grep -n "tracksToInsertBeforeMirror\|keys.mid(0, availableTracks)\|GroupType::AVSplit" src/timeline2/model/timelinemodel.cpp
# → mirror-gap arithmetic :1984-1999, stream fitting :2183, AVSplit grouping :2466
```

## Verdict
Adopt the ladder shape: census → single prompt → per-item validated insertion on shared accumulators → all-or-nothing undo → post-insertion grouping; and the compositing bracket (teardown before structural track changes, rebuild after, bracket lambdas pushed into BOTH undo and redo). Adapt the drop grammar (`A2/10/50`), the mirror-gap arithmetic, and the AutoTrackCreationDialog to your host's UI. Omit the target-lane (`m_audioTarget`/`m_binAudioTargets`) machinery unless your host has view-driven drop targets. Coverage caveat: no direct test covers any stage of this ladder — treat the quoted source as the only evidence until a fixture exists.
