<!-- capsule-v2 -->
# Time remap — how do you enable/disable a per-frame speed map on a clip whose producer must be rebuilt from the bin, without losing the user's remap curve or the clip's visible duration?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter must add "time remap" (a speed MAP, not a constant speed like timewarp) to clips: enabling swaps the producer to a chain containing a `timeremap` link; disabling must swap back AND restore the clip's on-timeline duration, which is only knowable by parsing the map string.

## Unplant → producer rebuild from bin → replant, with split-partner fan-out and input-duration restore
**Path/Symbol:** `src/timeline2/model/timelinemodel.cpp:TimelineModel::requestClipTimeRemap` public entry (7215–7241) + core overload (7243–7275); `src/timeline2/model/clipmodel.cpp:ClipModel::useTimeRemapProducer` (999–1035), `useTimeRemapProducer_lambda` (1037–1063), `hasTimeRemap` (475–492), `getRemapInputDuration` (653–677), resize-exemption guards (177, 194), `m_hasTimeRemap` cache (40, 942–946); `src/timeline2/model/groupsmodel.cpp:GroupsModel::getSplitPartner` (224–243).
**Signature:** `bool requestClipTimeRemap(int clipId, bool enable)`; core `bool requestClipTimeRemap(int clipId, bool enable, Fun &undo, Fun &redo)`; `bool ClipModel::useTimeRemapProducer(bool enable, Fun &undo, Fun &redo)`; `int ClipModel::getRemapInputDuration() const`.
**Data Shape:** the producer's parent is an MLT chain; remap state lives in the chain link whose `mlt_service == "timeremap"` with properties `time_map` ("t=frames;…" pairs), `pitch`, `image_mode`; `m_hasTimeRemap` is a cached bool flipped only when the live scan disagrees.

### Decisive source
```cpp
// timelinemodel.cpp:7215-7241 — public entry fans out to the AV-split partner FIRST, one shared accumulator
if (!enable || !m_allClips[clipId]->hasTimeRemap()) {
    Fun undo = []() { return true; };
    Fun redo = []() { return true; };
    int splitId = m_groups->getSplitPartner(clipId);
    bool result = true;
    if (splitId > -1) { result = requestClipTimeRemap(splitId, enable, undo, redo); }
    result = result && requestClipTimeRemap(clipId, enable, undo, redo);
    if (result) { PUSH_UNDO(undo, redo, i18n("Enable time remap")); Q_EMIT refreshClipActions(); return true; }
    return false;
}
return true;   // disabling a clip that has no remap is a no-op success
```
```cpp
// timelinemodel.cpp:7243-7275 — core = unplant / rebuild / replant, same shape as the timewarp kernel
int oldPos = getClipPosition(clipId);
int previousDuration = 0;
if (!enable && m_allClips[clipId]->hasTimeRemap()) {
    previousDuration = m_allClips[clipId]->getRemapInputDuration();   // captured BEFORE deletion
}
success = success && getTrackById(trackId)->requestClipDeletion(clipId, true, true, local_undo, local_redo, false, false);
success = success && m_allClips[clipId]->useTimeRemapProducer(enable, local_undo, local_redo);
success = success && getTrackById(trackId)->requestClipInsertion(clipId, oldPos, true, true, local_undo, local_redo, false, false);
if (success && !enable && previousDuration > 0) {
    requestItemResize(clipId, previousDuration, true, true, local_undo, local_redo);   // restore visible length
}
if (!success) { local_undo(); return false; }
UPDATE_UNDO_REDO(local_redo, local_undo, undo, redo);
```
```cpp
// clipmodel.cpp:999-1035 — read the curve BEFORE rebuilding, re-apply it AFTER
if (!enable) {
    // walk the current chain links; on mlt_service == "timeremap":
    remapProperties.insert("time_map", fromLink->get("time_map"));
    remapProperties.insert("pitch", fromLink->get("pitch"));
    remapProperties.insert("image_mode", fromLink->get("image_mode"));
}
auto operation = useTimeRemapProducer_lambda(enable, audioStream, remapProperties);
auto reverse = useTimeRemapProducer_lambda(!enable, audioStream, remapProperties);
if (operation()) { UPDATE_UNDO_REDO(operation, reverse, local_undo, local_redo); UPDATE_UNDO_REDO(local_redo, local_undo, undo, redo); return true; }
```
```cpp
// clipmodel.cpp:653-677 — input duration parsed out of the map string
QString mapData = link->get("time_map");
int min = GenTime(link->anim_get_double("time_map", getIn())).frames(pCore->getCurrentFps());
int max = -1;
for (auto &s : mapData.split(';')) {
    int val = GenTime(s.section('=', 1).toDouble()).frames(pCore->getCurrentFps());
    if (val > max) { max = val; }
}
return max - min;
```

**Flow:** (1) public entry: disabling a non-remapped clip returns true without touching anything; otherwise resolve the AV-split partner via `getSplitPartner` (the other leaf of the 2-leaf AVSplit group, -1 if absent or malformed) and run BOTH halves through the core overload into ONE undo/redo pair, pushing a single "Enable time remap" command; (2) core: capture `oldPos`; when DISABLING, capture `previousDuration = getRemapInputDuration()` (max map value − map value at the clip's in point) BEFORE the clip leaves the track; unplant via `requestClipDeletion`, rebuild the producer via `useTimeRemapProducer(enable)` (which itself reads the timeremap link's time_map/pitch/image_mode first, then calls `refreshProducerFromBin(..., TimeWarpInfo{enableRemap=enable})` and re-applies the saved properties onto the NEW chain's timeremap link — so the user's curve survives the bin rebuild), replant at `oldPos`, and when disabling restore the visible duration with `requestItemResize(clipId, previousDuration)`; any stage failure runs `local_undo()`; (3) resize exemption: `ClipModel::requestResize`'s max-duration guards carry `&& !hasTimeRemap()` (clipmodel.cpp:177/194) because a remapped clip's content length is defined by the map, not the source producer.
**Invariant:** the producer swap only takes effect through unplant/replant (same contract as timewarp-unplant-replant-kernel); the remap curve is captured BEFORE the rebuild and re-applied AFTER it, so enable→disable round-trips the exact time_map/pitch/image_mode; `previousDuration` is captured before deletion and restored after replant so the timeline geometry is unchanged by a disable; `m_hasTimeRemap` cache is flipped only when the live chain scan disagrees (clipmodel.cpp:942-946); the split partner is always processed before the primary clip within one stack entry.
**Probe:** NO direct test file exists for time remap (`grep -rl 'TimeRemap' tests/` → 0 files) — evidence gap recorded honestly; behavior anchors are the source guards above plus the shared primitives' tests (movetest/trimmingtest for delete+insert+resize composition). Deterministic probe below executed live.

## Get live surrounding code
**Retrieve:**
```bash
$ grep -n 'useTimeRemapProducer\|getRemapInputDuration\|hasTimeRemap' src/timeline2/model/clipmodel.cpp | head -18
40:    , m_hasTimeRemap(hasTimeRemap())
177:    if (!m_endlessResize && (size <= 0 || size > maxDuration) && !hasTimeRemap()) {
194:        if (right && (out - delta >= maxDuration) && !hasTimeRemap()) {
338:            if (hasTimeRemap()) {
475:bool ClipModel::hasTimeRemap() const
653:int ClipModel::getRemapInputDuration() const
895:    if (m_hasTimeRemap) {
942:    if (m_hasTimeRemap != hasTimeRemap()) {
943:        m_hasTimeRemap = !m_hasTimeRemap;
946:    if (m_hasTimeRemap) {
996:    refreshProducerFromBin(trackId, m_currentState, stream, 0, hasPitch, m_subPlaylistIndex == 1, hasTimeRemap());
999:bool ClipModel::useTimeRemapProducer(bool enable, Fun &undo, Fun &redo)
1027:    auto operation = useTimeRemapProducer_lambda(enable, audioStream, remapProperties);
1028:    auto reverse = useTimeRemapProducer_lambda(!enable, audioStream, remapProperties);
1037:Fun ClipModel::useTimeRemapProducer_lambda(bool enable, int audioStream, const QMap<QString, QString> &remapProperties)
1414:    if (m_hasTimeRemap) {
# executed live this pass; graph search_graph unavailable (MCP not connected in session)
```

## Verdict
Adopt the capture-before-swap / re-apply-after-swap pattern: whenever a producer is rebuilt from a canonical source (bin), any per-instance effect state that does not live in that source must be read first and written back after. Adopt the parse-the-map-for-duration trick (disable-time restore) instead of storing redundant geometry — it keeps the map string as the single source of truth. Adopt the split-partner-first fan-out with one shared accumulator (identical shape to requestClipTimeWarp's partner handling). Adapt the MLT chain/link walk to your host's effect-graph API; omit the pitch/image_mode passthrough unless your remap supports them. Porting risk: no repo test pins this plane — add your own round-trip test (enable → disable → duration + curve equal) before relying on it.
