<!-- capsule-v2 -->
# Resize proposal + trial — how do you snap a requested trim size, verify it fits, and never commit an unverified resize?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive`. **Question:** A porter must turn a raw mouse-driven size into a legal new size: snapped to nearby edges, clamped to blank capacity and mix boundaries, and proven feasible before the model commits.

## Transient playhead snap point → proposeSize → trial resize → temp_undo
**Path/Symbol:** `src/timeline2/model/timelinemodel.cpp:TimelineModel::requestItemResizeInfo` (4029–4104), `TimelineModel::requestItemResize` (4188–4513 public; functor overload 4515+), `src/timeline2/model/trackmodel.cpp:TrackModel::requestClipResize_lambda` (666–838).
**Signature:** `int requestItemResizeInfo(int itemId, int currentIn, int currentOut, int requestedSize, bool right, int snapDistance)` · `Fun requestClipResize_lambda(int clipId, int in, int out, bool right, bool hasMix, bool finalMove)`.
**Data Shape:** Returns a suggested/committed size or -1 on refusal. Resize-lambda decision tree shapes: no-op true functor when `delta == 0`; shrink inserts a blank of `delta-1` at the vacated side then resizes; grow-right "clip is last" always allowed; grow-left at playlist index 0 impossible; else blank-capacity check `blank_length + delta >= 0`.

### Decisive source
```cpp
// timelinemodel.cpp — proposal with transient playhead snap
int timelinePos = pCore->getMonitorPosition();
m_snaps->addPoint(timelinePos);
proposed_size = m_snaps->proposeSize(currentIn, currentOut, getBoundaries(itemId), requestedSize, right, snapDistance);
m_snaps->removePoint(timelinePos);
if (proposed_size > 0 && ...) {
    success = m_allClips[itemId]->requestResize(proposed_size, right, temp_undo, temp_redo, false, hasMix);
    // undo temp move
    temp_undo();
    if (success) requestedSize = proposed_size;
}
// trackmodel.cpp — grow-left boundary law
} else {
    if (target_clip == 0) {
        // clip is first, it can never be extended on the left
        return []() { return false; };
    }
```

**Flow:** mix-aware pre-clamp: growing across a non-blank neighbor clamps to `getBlankEnd/Start` extents (returns current size when nothing fits; over-large overshoot disables snapping) → snap proposal brackets the playhead as a temporary snap source → TRIAL resize executes against throwaway functors and is immediately rolled back via `temp_undo()` — only then is the size accepted → commit path fans out to all group members (`all_items`), computes each member's finalSize from the shared `finalPos`, aborts if any member would drop below 1 frame (result=false ⇒ full `undo()` + assert), adjusts/deletes mixes whose zone shrank away, and pushes ONE undo command for the whole fan-out.
**Invariant:** A proposed size is never trusted without a dry run; the playhead snap point exists ONLY between addPoint/removePoint; last-clip grow-right may extend indefinitely but must first bump the MLT producer length (`set("length", out+1)`); every failure path ends in executed rollback, not silent divergence.
**Probe:** `tests/trimmingtest.cpp:118-174` "Cut and resize": after splitting, `requestItemResize(splitted, l-3, true, true) == -1` (beyond blank), `== l` into freed space, `requestItemResize(cid1, 5, false, true) == -1`; undo×3/redo×3 restores exact state with `checkConsistency()`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "kdenlive", query: "requestItemResize resize clip trial snap", limit: 10 });
// executed live: rank 1 TimelineModel.requestItemResize timelinemodel.cpp:4515-4577;
// rank 2 TrackModel.requestClipResize_lambda trackmodel.cpp:666-838;
// rank 3 requestClipResizeAndTimeWarp :3887-4027
```

## Verdict
Adopt propose→trial→rollback ordering and the blank-capacity arithmetic. Adapt the playhead hook (`pCore->getMonitorPosition()`) to your host's cursor source, and replace MLT producer-length bumps with your renderer's duration API. Omit the mix cut/duration adjustment lambdas unless you port kdenlive-style mixes.
