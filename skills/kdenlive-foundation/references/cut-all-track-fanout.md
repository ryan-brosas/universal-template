<!-- capsule-v2 -->
# Cut-all track fan-out — how do you cut EVERY unlocked track (and every subtitle layer) at the playhead as one undo entry with all-or-nothing failure semantics?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter's "razor at playhead" must cut every clip sitting at one frame across all tracks plus all subtitle layers, yet behave as a single undo step where any single-track failure rolls back every cut already made.

## requestClipCutAll: census → subtitle layers → per-track cuts on ONE shared accumulator
**Path/Symbol:** `src/timeline2/model/timelinefunctions.cpp:TimelineFunctions::requestClipCutAll` (366–424); per-cut engine `requestClipCut` (258–364); track census `TrackModel::shouldReceiveTimelineOp` (`trackmodel.cpp:1622–1626`); layer lookup `TimelineModel::getClipByPosition(trackId, position, playlistOrLayer)` (`timelinemodel.cpp:465–473`).
**Signature:** `bool requestClipCutAll(std::shared_ptr<TimelineItemModel> timeline, int position)` — note: NO Fun parameters; it owns its own accumulators and the single `pCore->pushUndo`.
**Data Shape:** local `undo`/`redo` Fun initialized to no-op lambdas; `affectedTracks` = tracks where `shouldReceiveTimelineOp()` (timeline_active && !locked); subtitle layers probed with trackId **-2** via `getClipByPosition(-2, position, layer)` for layer in [0, getMaxLayer()).

### Decisive source
```cpp
// timelinefunctions.cpp:369-424 — the fan-out and its all-or-nothing guard
std::function<bool(void)> undo = []() { return true; };
std::function<bool(void)> redo = []() { return true; };

for (const auto &track : timeline->m_allTracks) {
    if (track->shouldReceiveTimelineOp()) {          // active AND unlocked only
        affectedTracks << track;
    }
}
...
if (subModel && !subModel->isLocked()) {
    for (int layer = 0; layer < subModel->getMaxLayer(); layer++) {
        int clipId = timeline->getClipByPosition(-2, position, layer);
        if (clipId > -1) {
            if (!TimelineFunctions::requestClipCut(timeline, clipId, position, undo, redo)) {
                pCore->displayMessage(i18n("Failed to cut clip"), ErrorMessage, 500);
                bool undone = undo();                 // roll back ALL cuts made so far
                Q_ASSERT(undone);
                return false;
            }
            count++;
        }
    }
}
if (affectedTracks.isEmpty() && count == 0) {
    pCore->displayMessage(i18n("All tracks are locked"), ErrorMessage, 500);
    return false;
}
for (auto track : std::as_const(affectedTracks)) {
    int clipId = track->getClipByPosition(position);
    if (clipId > -1) {
        if (!TimelineFunctions::requestClipCut(timeline, clipId, position, undo, redo)) {
            ... bool undone = undo(); Q_ASSERT(undone); return false;   // same all-or-nothing
        }
        count++;
    }
}
if (!count) {
    pCore->displayMessage(i18n("No clips to cut"), ErrorMessage);
} else {
    pCore->pushUndo(undo, redo, i18n("Cut all clips"));   // ONE undo entry for the whole fan-out
}
return count > 0;
```

**Flow:** (1) build the affected-track census from `shouldReceiveTimelineOp()` (skips locked and non-timeline-active tracks entirely — they are neither cut nor reported as failures); (2) walk subtitle layers first (track sentinel -2, one probe per layer), cutting each subtitle event found at the position through the same `requestClipCut` engine; (3) walk every affected track, cutting the clip found at the position; (4) every cut appends to the SAME local `undo`/`redo` accumulators — there is no per-track undo entry; (5) any failed cut runs the shared `undo()` (rolling back all prior cuts in this fan-out), Q_ASSERTs it succeeded, and returns false with a user message; (6) zero cuts = "No clips to cut" message, no stack push; ≥1 cut = ONE `pushUndo("Cut all clips")`.
**Invariant:** all-or-nothing — a partial fan-out is never left on the stack; locked tracks are silently excluded from the census (not errors); the empty-cut case (nothing at the position anywhere) is a TRUE return with count==0 and NO undo entry pushed; the accumulators start as no-op lambdas so the first real mutation defines the rollback boundary.
**Probe:** `tests/movetest.cpp:96-107` "Ensure selected group cut works" exercises cut under an active selection with undo/redo cycles; per-cut semantics are pinned by `tests/trimmingtest.cpp:60-92` (empty cuts return true, no-op) and `tests/trimmingtest.cpp:444-531` (group-scoped cut). No dedicated requestClipCutAll test section exists — evidence gap recorded.

## Get live surrounding code
**Retrieve:**
```bash
$ grep -n 'requestClipCutAll\|shouldReceiveTimelineOp' src/timeline2/model/timelinefunctions.cpp src/timeline2/model/trackmodel.cpp
src/timeline2/model/timelinefunctions.cpp:366:bool TimelineFunctions::requestClipCutAll(std::shared_ptr<TimelineItemModel> timeline, int position)
src/timeline2/model/trackmodel.cpp:1622:bool TrackModel::shouldReceiveTimelineOp() const
$ grep -n 'getClipByPosition(int trackId' src/timeline2/model/timelinemodel.cpp
465:int TimelineModel::getClipByPosition(int trackId, int position, int playlistOrLayer) const
# executed live this pass; graph search_graph unavailable (MCP not connected in session)
```

## Verdict
Adopt the fan-out shape: census first (skip locked lanes silently), then per-lane cuts on ONE shared accumulator, all-or-nothing rollback with Q_ASSERT, single push at the end only when count > 0. Adopt the "empty result is success with no undo entry" contract — it keeps razor tools idempotent. Adapt the subtitle-layer walk (sentinel track -2) to your host's overlay-item model, or omit it. Omit the i18n/displayMessage plumbing. Porting risk: no dedicated test pins the fan-out itself; if your port adds one, the natural fixture is two tracks where the second cut fails (e.g. a locked-track edge) asserting the first cut was rolled back.
