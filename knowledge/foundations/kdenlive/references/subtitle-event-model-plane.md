<!-- capsule-v2 -->
# Subtitle event-model plane — how do you model a subtitle track whose items are NOT playlist entries (filter-rendered events) yet still participate in groups, snapping, locks, and fake-position view projection?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter has a secondary item type (subtitles/captions) that is rendered by an effect over a side file, not by the main playlist — but the UI treats it like a track: items can be grouped with clips, snapped to, locked, moved by ripples, cut at a frame, and resized. How does the model stay honest?

## Event-map storage + validation ladder + razor-mode cut + rekeying resize + lock/fake-pos integration
**Path/Symbol:** `src/bin/model/subtitlemodel.hpp` (whole 343L — note: lives in `src/bin/model`, NOT timeline2), `subtitlemodel.cpp:addSubtitle` Fun variant (434–457) + core (459–497), `cutSubtitle` both overloads (663–727), `requestResize` both overloads (824–905), `removeSubtitle` (972–1010), `getSubtitleFakePosition` (1343), `doCutSubtitle` (1637–1670), `setSubtitleFakePosFromIndex` (2113); integration points `src/timeline2/model/timelinemodel.cpp:requestSubtitleDeletion` (2765–2780), group-move fake-position phase (3010–3012), locked-subtitle group abort (3254–3257), `getItemFakePosition` dispatch (6358–6367), paste add (pasteTimelineClips ~2840).
**Signature:** `bool addSubtitle(std::pair<int, GenTime> start, const SubtitleEvent &event, Fun &undo, Fun &redo, bool updateFilter = true)`; `int cutSubtitle(int layer, int position, Fun &undo, Fun &redo)`; `bool requestResize(int id, int size, bool right, Fun &undo, Fun &redo, bool logUndo)`; `bool removeSubtitle(int id, bool temporary = false, bool updateFilter = true)`.
**Data Shape:** `std::map<std::pair<int /*layer*/, GenTime /*start*/>, SubtitleEvent> m_subtitleList` (sorted by layer then start) + id index `std::map<int, std::pair<int, GenTime>> m_allSubtitles`; the MLT `m_subtitleFilter` reads a JSON side file rewritten on `modelChanged()`; `m_subtitlesFakePos` maps row index → fake start frame for in-flight view projection.

### Decisive source
```cpp
// subtitlemodel.cpp:459-497 — the validation ladder BEFORE any mutation
if (start.second.frames(...) < 0 || event.endTime().frames(...) < 0 || isLocked()) { return false; }
if (start.second.frames(...) > event.endTime().frames(...)) { return false; }        // start must precede end
if (m_subtitleList.count(start) > 0) { return false; }                               // no two subs at same (layer,start)
if (start.first > m_maxLayer || start.first < 0) { return false; }
registerSubtitle(id, start, temporary);
m_subtitleList[start] = event;
m_subtitleList[start].setText(event.text().trimmed());   // strip leading/trailing whitespace (SRT export hygiene)
addSnapPoint(start.second);
addSnapPoint(event.endTime());                            // BOTH edges feed the shared snap grid
if (!temporary && event.endTime().frames(...) > m_timeline->duration()) {
    m_timeline->updateDuration();                         // subtitles can EXTEND the timeline duration
}
```
```cpp
// subtitlemodel.cpp:674-727 — cutSubtitle: razor mode decides the text split, geometry split reuses requestResize
if (KdenliveSettings::subtitle_razor_mode() == RAZOR_MODE_DUPLICATE) {
    leftText = originalText; rightText = originalText;
} else if (... == RAZOR_MODE_AFTER_FIRST_LINE) {
    QRegularExpressionMatch newlineMatch = newlineRe.match(originalText);
    if (!newlineMatch.hasMatch()) { undo(); return -1; }   // no line break → cut refused
    leftText.truncate(newlineMatch.capturedStart());
    rightText = originalText.right(originalText.length() - newlineMatch.capturedEnd());
}
int duration = position - start.frames(pCore->getCurrentFps());
bool res = requestResize(subId, duration, true, undo, redo, false);   // shrink original to the cut frame
if (res) {
    int id = TimelineModel::getNextId();                              // NEW id from the SAME global counter
    Fun local_redo = [this, id, layer, pos, originalEvent, subId, leftText, rightText]() {
        editSubtitle(subId, leftText);
        return addSubtitle(id, {layer, pos}, SubtitleEvent(originalEvent.isDialogue(), ..., rightText));
    };
    if (local_redo()) { UPDATE_UNDO_REDO(local_redo, local_undo, undo, redo); return id; }
}
undo();
return -1;
```
```cpp
// subtitlemodel.cpp:888-905 — LEFT resize REKEYS the map entry (start is part of the key!)
std::pair<int, GenTime> newStartPos = {startPos.first, endPos - GenTime(size, pCore->getCurrentFps())};
if (m_subtitleList.count(newStartPos) > 0) { return false; }          // occupied slot → abort
operation = [this, id, startPos, newStartPos, event, logUndo]() {
    m_allSubtitles[id] = newStartPos;
    m_subtitleList.erase(startPos);
    m_subtitleList[newStartPos] = event;                              // erase+insert = move in the sorted map
    removeSnapPoint(startPos.second);
    addSnapPoint(newStartPos.second);
    ...
};
```
```cpp
// timelinemodel.cpp:2765-2780 — deletion goes through the timeline's Fun discipline, first/last gate the filter rewrite
Fun operation = [this, clipId, last]() { return m_subtitleModel->removeSubtitle(clipId, false, last); };
Fun reverse = [this, clipId, layer, startTime, sub, first]() { return m_subtitleModel->addSubtitle(clipId, {layer, startTime}, sub, false, first); };
if (operation()) { UPDATE_UNDO_REDO(operation, reverse, undo, redo); return true; }
```
```cpp
// timelinemodel.cpp:3010-3012 + 3254-3257 — same forest, same lock gates as clips
if (isSubTitle(item)) {
    int ix = m_subtitleModel->getSubtitleIndex(item);
    int target_position = old_position[item] + delta_pos;
    m_subtitleModel->setSubtitleFakePosFromIndex(ix, target_position);   // fake pos during group-move view phase
    all_subs.emplace(item);
}
...
if (!sorted_subtitles.empty() && m_subtitleModel->isLocked()) {
    return false;                                                       // group containing a locked subtitle aborts
}
```

**Flow:** (1) storage: a subtitle is a `(layer, startGenTime) → SubtitleEvent` entry plus an id→key index — there is NO playlist, NO producer per item; rendering happens through one MLT filter whose JSON side file is rewritten when `updateFilter`/`modelChanged()` fires (the `first`/`last` flags on add/remove let a batch of deletions rewrite the file once); (2) every mutation entry point (add/remove/cut/resize) starts with the same ladder: locked → refuse, negative/inverted times → refuse, duplicate slot → refuse, layer bounds → refuse; (3) cut = geometry shrink of the original via `requestResize` + insertion of a NEW-id sibling carrying the right-hand text, with the text split policy (duplicate vs after-first-line) as a user setting — a cut without a line break in after-first-line mode is REFUSED, not silently duplicated; (4) right resize mutates the event's end time; LEFT resize must erase-and-reinsert because the start time IS the map key, and an occupied target slot aborts; (5) both edges register into the shared snap grid through the registered snap models (weak_ptr, pass-1 plane), so clips snap to subtitle edges and vice versa; (6) integration: subtitles join the group forest as ordinary items (group moves carry them via fake positions in the view phase, and a locked subtitle aborts the whole group move), deletion goes through `requestSubtitleDeletion`'s operation/reverse lambdas on the shared accumulators, and paste adds them through the same Fun variant.
**Invariant:** one global id space (TimelineModel::getNextId) for clips, compositions, AND subtitles; the `(layer,start)` key makes "two subtitles starting at the same frame on one layer" unrepresentable; every mutation is lock-gated at the model boundary (not just at call sites); the filter side file is the only durable artifact and is rewritten lazily (first/last flags batch it); snap registration is symmetric — subtitle edges are first-class snap points.
**Probe:** tests/subtitlestest.cpp (whole 323L) pins import behavior: exact GenTime boundaries (140/265/503/628/628/875 @25fps), broken-file recovery (2 of 3 dialogues), whitespace trimming ("\n   some more whitespaces  \n" → "some more whitespaces"), ASS comma handling, SBV/VTT loading, non-UTF-8 encoding guess. Cut/resize/lock paths have NO dedicated test — evidence gap recorded. Deterministic probes below executed live.

## Get live surrounding code
**Retrieve:**
```bash
$ grep -n 'RAZOR_MODE\|cutSubtitle' src/bin/model/subtitlemodel.cpp
663:bool SubtitleModel::cutSubtitle(int layer, int position)
667:    if (cutSubtitle(layer, position, undo, redo) > -1) {
674:int SubtitleModel::cutSubtitle(int layer, int position, Fun &undo, Fun &redo)
692:        if (KdenliveSettings::subtitle_razor_mode() == RAZOR_MODE_DUPLICATE) {
695:        } else if (KdenliveSettings::subtitle_razor_mode() == RAZOR_MODE_AFTER_FIRST_LINE) {
1653:        int newId = cutSubtitle(layer, timelinePos, undo, redo);
$ grep -n 'setSubtitleFakePosFromIndex\|getSubtitleFakePosition' src/timeline2/model/timelinemodel.cpp src/bin/model/subtitlemodel.cpp
src/timeline2/model/timelinemodel.cpp:3012:            m_subtitleModel->setSubtitleFakePosFromIndex(ix, target_position);
src/timeline2/model/timelinemodel.cpp:6367:        return m_subtitleModel->getSubtitleFakePosition(itemId);
src/bin/model/subtitlemodel.cpp:1343:int SubtitleModel::getSubtitleFakePosition(int sid) const
src/bin/model/subtitlemodel.cpp:2113:void SubtitleModel::setSubtitleFakePosFromIndex(int index, int pos)
# executed live this pass; graph search_graph unavailable (MCP not connected in session)
```

## Verdict
Adopt the event-map-with-side-file shape for any secondary item type rendered by an effect rather than stored in the main sequence: keep the model as the single source of truth, make the rendered artifact a lazy rewrite gated by first/last batch flags, and share the global id counter so secondary items can join the primary item's group/selection machinery unchanged. Adopt the key-includes-position discipline (left-resize = erase+reinsert with occupancy check) whenever your container is keyed by geometry. Adopt lock-gating at the model boundary plus the "locked member aborts the whole group op" rule. Adapt the razor-mode setting to your host's text-split policy; omit the SRT/ASS/VTT parsers (codec work) unless you need import. Porting risk: no repo test covers cut/resize/lock — add fixtures pinning the duplicate-slot refusal, the no-line-break cut refusal, and the locked-subtitle group abort before relying on them.
