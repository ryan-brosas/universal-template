<!-- capsule-v2 -->
# Group two-phase move — how do you move N grouped items without the group colliding with itself?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive`. **Question:** A porter must move a set of clips/compositions/subtitles as one rigid block across tracks and positions, where naive per-item relocation makes members collide with each other.

## Remove-all, then reinsert, sorted by move direction
**Path/Symbol:** `src/timeline2/model/timelinemodel.cpp:TimelineModel::requestGroupMove` (3102–3168 selection dance; 3170–3490+ functor overload with clamping ladder and two-stage execution).
**Signature:** `bool requestGroupMove(int itemId, int groupId, int delta_track, int delta_pos, bool updateView, bool finalMove, Fun &undo, Fun &redo, bool revertMove, bool moveMirrorTracks, bool allowViewRefresh = true, const QVector<int> &allowedTracks = {})`.
**Data Shape:** Inputs: anchor item + its group root id, integer track/position deltas. Internal buckets: `sorted_clips` (id→old position), `sorted_compositions` (id→{position, MLT track index}), `sorted_subtitles` (id→{layer, GenTime}), `mixesToDelete` snapshotted BEFORE any mutation, `clipsByTrack`/`composByTrack` for batched view updates.

### Decisive source
```cpp
// Moving groups is a two stage process: first we remove the clips from the tracks, and then try to
// insert them back at their calculated new positions.
// This way, we ensure that no conflict will arise with clips inside the group being moved
...
// Sort compositions. We need to delete in the move direction from top to bottom
std::sort(sorted_compositions.begin(), sorted_compositions.end(),
          [delta_track, delta_pos](...){ ... });   // by MLT index when delta_track!=0 else position
if (delta_track != 0) {
    // We delete our clips only if changing track
    for (const std::pair<int,int> &item : sorted_clips) {
        ok = ok && getTrackById(old_trackId)->requestClipDeletion(item.first, ...);
        if (!ok) { bool undone = local_undo(); Q_ASSERT(undone); return false; }
    }
}
```

**Flow:** gather `m_groups->getLeaves(groupId)` → bucket by kind → clamp `delta_track`: compute lower/upper occupied track positions; video/audio master semantics flip audio_delta or video_delta sign; out-of-bounds or wrong-type destination clamps delta_track to 0 (fall back horizontal); per-item destination emptiness via `isAvailableWithExceptions(newIn, playtime-1, sorted ids)` → same-track path instead checks collisions per track and may SUGGEST a smaller delta (blank-start clamping) → stage 1: delete mixes whose partner leaves the group, then remove all items (only when changing track) → stage 2: reinsert each item at old+delta with per-kind ordering → compose everything into undo/redo functors; any failure ⇒ `local_undo()` + assert + false.
**Invariant:** Intra-group items can never collide because every member is off-track before any reinsertion; `delta_track == 0 && delta_pos == 0` aborts (nothing to do); subtitles never move below frame 0 (delta clamped, abort at 0).
**Probe:** `tests/groupstest.cpp:27-149` pins the underlying forest queries (`getRootId`, `getLeaves(2)=={0,4,6,7,9}`, subtree sets after reparenting) that feed this seam; timeline-level group moves are exercised through `tests/modeltest.cpp` move suites with `checkConsistency()` after each step.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "kdenlive", query: "groups model subtree walk hierarchy", limit: 30 });
// executed live: rank 1 GroupsModel.getSubtree groupsmodel.cpp:247-263;
// breakAffectedGroup timelinefunctions.cpp:751-775; GroupsModel.copyGroups :716-739
```

## Verdict
Adopt the two-phase discipline, direction-aware sorting, and pre-mutation mix snapshotting — they are storage-agnostic. Adapt the A/V mirror-delta algebra only if your host has no audio/video duality. Omit MLT mix (MixInfo) bookkeeping details if your renderer composites differently, but keep "snapshot cross-references BEFORE mutation" as law.
