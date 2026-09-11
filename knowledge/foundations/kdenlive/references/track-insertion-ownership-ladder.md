<!-- capsule-v2 -->
# Track insertion ownership ladder — how do you insert a track whose undo entry must keep the object alive, with globally unique ids?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive`. **Question:** A porter must add a track at an arbitrary position so that (a) undo doesn't dangle a destroyed object, (b) compositions targeting the insertion point follow it, and (c) every track/clip/composition/group id stays unique forever.

## Capture the inverse BEFORE constructing; redo holds a shared_ptr
**Path/Symbol:** `src/timeline2/model/timelinemodel.cpp:TimelineModel::requestTrackInsertion` (5213–5299), `TimelineModel::getNextId` (5881–5884), `requestTrackDeletion` (5301–5320 last-track guard).
**Signature:** `bool requestTrackInsertion(int position, int &id, const QString &trackName, bool audioTrack, Fun &undo, Fun &redo, bool addCompositing)` · `int getNextId() { return KdenliveDoc::next_id++; }`.
**Data Shape:** `position == -1` appends; out-of-range returns false. Emits back the allocated id. Composition retargeting list: all compositions whose `getATrack() == position && getForcedTrack() == -1`.

### Decisive source
```cpp
int trackId = TimelineModel::getNextId();
id = trackId;
Fun local_undo = deregisterTrack_lambda(trackId);          // capture inverse FIRST
TrackModel::construct(shared_from_this(), trackId, position, trackName, audioTrack, addCompositing);
...
Fun local_redo = [track, position, local_update, addCompositing, this]() {
    // We capture a shared_ptr to the track, which means that as long as this undo object lives,
    // the track object is not deleted. To insert it back it is sufficient to register it.
    registerTrack(track, position, true);
    ...
};
```

**Flow:** allocate id from ONE document-global counter shared by tracks/clips/compositions/groups → capture deregistration as undo → eagerly construct (mutation happens now; push-time redo is suppressed by the m_undone latch of the Fun kernel) → shift compositions that targeted the insert position (`setATrack(position+1)` on redo path, `(position)` on undo) → refresh track-tag roles for audio-below layout → compose via PUSH_LAMBDA/UPDATE_UNDO_REDO. Deletion refuses when `m_allTracks.size() < 2` with a user message, and discards running jobs for the object first (`pCore->taskManager.discardJobs`).
**Invariant:** Ids are never reused and come from a single counter — tests assert zero collisions across random track+clip interleavings; the undo command's captured `shared_ptr<TrackModel>` is the ownership anchor: while the command lives on the stack, the "deleted" track object remains constructible.
**Probe:** `tests/modeltest.cpp:1258-1307` "Check id unicity" — 20 random `TrackModel::construct` / `ClipModel::construct` calls, `REQUIRE(all_ids.count(tid) == 0)` each time plus final `checkConsistency()`; `tests/modeltest.cpp:16-73` "Basic creation/deletion of a track" round-trips `undoStack->undo()`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "kdenlive", query: "requestTrackInsertion requestTrackDeletion", limit: 15 });
// executed live (name_pattern): requestTrackDeletion timelinemodel.cpp:5322-5429;
// requestTrackInsertion timelinemodel.cpp:5213-5299 — both hits exact
```

## Verdict
Adopt: single monotonic id space, inverse-captured-before-mutation ordering, shared_ptr-in-command ownership, forced-track exemption when retargeting effects. Adapt `KdenliveSettings::audiotracksbelow()` view refresh to your layout policy. Omit MLT tractor/field wiring inside TrackModel::construct — replace with your renderer's track creation call.
