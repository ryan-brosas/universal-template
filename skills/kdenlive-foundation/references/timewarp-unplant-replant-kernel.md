<!-- capsule-v2 -->
# Timewarp — how do you change a clip's speed when the producer itself must be swapped, and the swap only takes effect on replant?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter must apply a speed change (or speed+resize composite) to a clip whose media producer is replaced by a timewarp variant; the new producer is invisible until the clip is unplanted and replanted into its track, and AV-split partners plus selected neighbors must follow.

## Unplant → swap producer → replant kernel + resize-and-warp composite
**Path/Symbol:** `src/timeline2/model/timelinemodel.cpp:TimelineModel::requestClipTimeWarp` core (7189–7213) and public entry (7277–7313), `requestClipResizeAndTimeWarp` (3887–4027); `src/timeline2/model/clipmodel.cpp:ClipModel::useTimewarpProducer` (1065–1133).
**Signature:** `bool requestClipTimeWarp(int clipId, double speed, bool pitchCompensate, bool changeDuration, Fun &undo, Fun &redo)` / `bool useTimewarpProducer(double speed, bool pitchCompensate, bool changeDuration, Fun &undo, Fun &redo)` / `int requestClipResizeAndTimeWarp(int itemId, int size, bool right, int snapDistance, bool allowSingleResize, double speed)`.
**Data Shape:** `previousSpeed`, `oldIn/oldOut` captured BEFORE the swap; `speedRatio = |previousSpeed / speed|`; `newDuration = qMax(1, round(oldDuration * speedRatio))`; `revertSpeed` = sign flip of speed; per-item `view_redo` lambda capturing invalidate zone + durationChanged flag.

### Decisive source
```cpp
// timelinemodel.cpp:7189-7213 — the unplant/replant sandwich; comment states WHY
int oldPos = getClipPosition(clipId);
// in order to make the producer change effective, we need to unplant / replant the clip in its track
bool success = true;
int trackId = getClipTrackId(clipId);
if (trackId != -1) success = success && getTrackById(trackId)->requestClipDeletion(clipId, true, true, local_undo, local_redo, false, false);
if (success)       success = m_allClips[clipId]->useTimewarpProducer(speed, pitchCompensate, changeDuration, local_undo, local_redo);
if (trackId != -1) success = success && getTrackById(trackId)->requestClipInsertion(clipId, oldPos, true, true, local_undo, local_redo, false, false);
if (!success) { local_undo(); return false; }
UPDATE_UNDO_REDO(local_redo, local_undo, undo, redo);
```
```cpp
// clipmodel.cpp:1065-1100 — duration math + sign-flip in/out shift + shrink-compensating reverse
if (m_endlessResize) return false;                       // no timewarp for endless producers
double previousSpeed = getSpeed();
const double speedRatio = std::fabs(previousSpeed / speed);
int newDuration = qMax(1, int(qRound64(double(oldDuration) * speedRatio)));
bool revertSpeed = false;
if (speed < 0) { if (previousSpeed > 0) revertSpeed = true; }
else if (previousSpeed < 0) revertSpeed = true;
auto operation = useTimewarpProducer_lambda(speed, audioStream, pitchCompensate);
auto reverse   = useTimewarpProducer_lambda(previousSpeed, audioStream, hasPitch);
if (revertSpeed || (changeDuration && oldOut >= newDuration)) {
    // we are going to shrink the clip when changing the producer. We must undo that when reloading the old producer
    reverse = [reverse, oldIn, oldOut, this]() { bool res = reverse(); if (res) setInOut(oldIn, oldOut); return res; };
}
if (revertSpeed) {
    int in  = qMax(0, int(qRound64(double(m_producer->get_length() - oldOut - 1) * speedRatio)));
    int out = in + newDuration;                          // negative speed plays from the END backwards
    operation = [operation, in, out, this]() { bool res = operation(); if (res) setInOut(in, out); return res; };
}
```

**Flow:** (1) public entry short-circuits with `qFuzzyCompare(speed, currentSpeed) && same pitchCompensate`; UI percentages are divided by 100 at the boundary; an AV-split partner is warped FIRST (same speed on both halves, one undo entry); an uninserted (bin) clip only swaps its producer — no track dance; (2) core kernel: delete from track → `useTimewarpProducer` (swap MLT producer to timewarp variant carrying speed/pitch; recompute in/out; if `changeDuration`, clamp final playtime to `qMin(newDuration, getMaxDuration()-getIn())` via a follow-up `requestResize` so the clip can never exceed source material or drop below one frame) → reinsert at `oldPos`; any failure runs `local_undo()`; (3) `requestClipResizeAndTimeWarp` composes per item: delete → warp → resize → reinsert, where selection-only items are scaled by the speed ratio (`itemSize = playtime * |clipSpeed| / |speed|`) and the split partner joins only when edge-aligned (right resize: `out == end`; left: `start == in`); each item pushes its `view_redo` (invalidateZone/invalidateAudioZone + updateDuration) onto BOTH undo and redo so view state tracks every step; total failure undoes everything and reports a TYPED error distinguishing "cannot resize this clip" vs "the corresponding split clip" vs "one or more clips in the selection".
**Invariant:** a producer swap without unplant/replant is a no-op by construction — the kernel makes that impossible; `newDuration >= 1` always (one-frame floor); sign-flipped speed re-anchors in/out at the END of the source (`length - oldOut - 1` scaled) so reversed playback starts where forward playback ended; the reverse lambda restores `oldIn/oldOut` exactly when the swap shrank the clip, so undo never leaves a shorter clip behind; endless producers refuse timewarp outright.
**Probe:** `tests/timewarptest.cpp:44-99`: orphan clip 1.0→0.1 gives `playtime == originalDuration / 0.1` exactly, undo restores both speed and duration, 0.1→1.2 rescales from the CURRENT duration; `requestClipTimeWarp(cid3, curLength)` succeeds with `playtime == 1` (the floor), while `curLength * 10` is REFUSED (`REQUIRE_FALSE`) — a clip can never be warped below one frame.

## Get live surrounding code
**Retrieve:**
```bash
$ grep -n 'requestClipTimeWarp\|useTimewarpProducer' src/timeline2/model/timelinemodel.cpp
3969:        result = result && requestClipTimeWarp(id, speed, pitchCompensate, true, undo, redo);
7189:bool TimelineModel::requestClipTimeWarp(int clipId, double speed, bool pitchCompensate, bool changeDuration, Fun &undo, Fun &redo)
7202:        success = m_allClips[clipId]->useTimewarpProducer(speed, pitchCompensate, changeDuration, local_undo, local_redo);
7277:bool TimelineModel::requestClipTimeWarp(int clipId, double speed, bool pitchCompensate, bool changeDuration)
7293:            result = requestClipTimeWarp(splitId, speed / 100.0, pitchCompensate, changeDuration, undo, redo);
$ grep -n 'useTimewarpProducer' src/timeline2/model/clipmodel.cpp
1065:bool ClipModel::useTimewarpProducer(double speed, bool pitchCompensate, bool changeDuration, Fun &undo, Fun &redo)
1089:    auto operation = useTimewarpProducer_lambda(speed, audioStream, pitchCompensate);
1090:    auto reverse = useTimewarpProducer_lambda(previousSpeed, audioStream, hasPitch);
# executed live this pass; graph search_graph unavailable (MCP not connected in session)
```

## Verdict
Adopt the unplant→swap→replant sandwich as the universal pattern for ANY in-place media-attribute change your host's compositor only honors on replant (speed, deinterlace, pixel format). Adopt the captured-previous-state reverse with explicit in/out restoration for shrinking swaps, the one-frame floor via `qMax(1, ...)`, and the partner-first ordering for paired items. Adapt the percentage-at-boundary convention (`speed/100.0`) to your API; omit the selection-scaling fan-out unless you port multi-select resize. The typed three-way failure message (main/split/selection) is worth copying verbatim as a UX contract.
