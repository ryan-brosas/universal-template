<!-- capsule-v2 -->
# Consistency prover walk — how do you give a mutable document model a self-prover that catches every class of drift the mutation kernels could introduce (parent links, snap-grid refcounts, bin registration, render-graph mirroring) without trusting any single registry?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive`. **Question:** after dozens of overlapping mutation kernels (move, resize, group, mix, zone, load) touch the same model, what single function proves nothing drifted — and what does each of its passes catch?

## The model's own invariant prover
**Path/Symbol:** `src/timeline2/model/timelinemodel.cpp:TimelineModel::checkConsistency` (:6727-6925); base prover `src/abstractmodel/abstracttreemodel.cpp:AbstractTreeModel::checkConsistency` (:201-260); document-level fan-out `src/doc/kdenlivedoc.cpp:KdenliveDoc::checkConsistency` (:2488-2500).
**Signature:** `bool TimelineModel::checkConsistency(const std::vector<int> &guideSnaps = {})` (timelinemodel.hpp:1062).
**Data Shape:** input: optional extra guide snap frames (default empty; the parameter exists for tests, exposed via friend declarations on projectclip.h:55 / sequenceclip.h:48 / playlistclip.h:50 so the prover can read `m_registeredClipsByUuid`). Output: bool; every failure path emits a `qWarning` naming the drift class before returning false.

### Decisive source
```cpp
// timelinemodel.cpp:6766-6807 — rebuild the snap map from scratch, compare exactly
if (getClipTrackId(cp.first) != -1) {
    snaps[clip->getPosition()] += 1;
    snaps[clip->getPosition() + clip->getPlaytime()] += 1;
    if (clip->getMixDuration() > 0) {
        snaps[clip->getPosition() + clip->getMixDuration() - clip->getMixCutPosition()] += 1;
    }
}
...
for (auto p : guideSnaps) { snaps[p] += 1; }

// Check snaps
auto stored_snaps = m_snaps->_snaps();
if (snaps.size() != stored_snaps.size()) {
    qWarning() << "Wrong number of snaps" << snaps.size() << stored_snaps.size();
    return false;
}
for (auto i = snaps.begin(), j = stored_snaps.begin(); i != snaps.end(); ++i, ++j) {
    if (*i != *j) {
        qWarning() << "Wrong snap info at point" << (*i).first;
        return false;
    }
}
```
```cpp
// timelinemodel.cpp:6845-6893 — render-graph reconciliation by set difference
std::unordered_set<int> remaining_compo;
for (const auto &compo : m_allCompositions) { ... remaining_compo.insert(compo.first); }
QScopedPointer<Mlt::Field> field(m_tractor->field());
field->block();
mlt_service nextservice = mlt_service_get_producer(field->get_service());
...
while (nextservice != nullptr) {
    if (mlt_type == mlt_service_transition_type) {
        auto tr = mlt_transition(nextservice);
        if (mlt_properties_get_int(MLT_TRANSITION_PROPERTIES(tr), "internal_added") > 0) {
            // Skip track compositing
            nextservice = mlt_service_producer(nextservice); continue;
        }
        int currentTrack = mlt_transition_get_b_track(tr);
        int currentATrack = mlt_transition_get_a_track(tr);
        if (currentTrack == currentATrack) {
            // Skip invalid transitions created by MLT on track deletion
            nextservice = mlt_service_producer(nextservice); continue;
        }
        ...
        // match against remaining_compo by (track, a_track, in, out); erase on match
        if (foundId == -1) { field->unblock(); return false; }
        remaining_compo.erase(foundId);
    }
    ...
}
if (!remaining_compo.empty()) { ... return false; }
```

**Flow:** seven ordered passes, each catching one drift class: (1) per-track parent link (`m_parent.lock().get() == this`) + per-track `checkConsistency`; (2) per-clip parent link + snap-map contribution (in, in+playtime, and the mix-adjusted point `pos + mixDuration - mixCutPosition` when a mix exists) + per-clip `checkConsistency`; (3) per-composition parent link + in/out snap contribution; (4) guideSnaps appended, then the rebuilt map compared to the live `m_snaps` grid — size first, then key-and-refcount equality element-wise (this catches any kernel that forgot an addSnapPoint/removeSnapPoint pair); (5) bin-registration cross-check in BOTH directions: every bin clip's registered timeline refs must exist in the timeline, and every timeline clip must be registered in its bin clip's `m_registeredClipsByUuid[uuid()]`; (6) render-graph reconciliation: walk the MLT field's service chain under `field->block()`, skip `internal_added` (track compositing) and `a_track == b_track` (MLT's own track-deletion artifacts), match each remaining transition against `m_allCompositions` by (b_track, a_track, in, out), erase on match; the remaining set must end empty — catches both phantom transitions and unplanted compositions; (7) group forest consistency (`m_groups->checkConsistency(true, true)`) and a final selection sanity check (a single non-clip/non-composition/non-subtitle/non-group id is invalid).

**Invariant:** the prover trusts NO single registry — every cross-cutting invariant is recomputed from primary state (clip positions, composition records, the field's service chain) and compared against the derived/secondary state (snap grid, bin registration, planted transitions). It is side-effect-free on success: the field is blocked only for the walk and unblocked on every exit path. The tests use it as their oracle: `tests/test_utils.cpp:284` asserts `model->checkConsistency()` after every operation, and 775 call sites across 14 test files depend on it.

**Probe:** no dedicated test file exists for the prover itself (its guideSnaps parameter is exercised only via the default `{}` in the test helper — caveat recorded). Executed deterministic probe:
```
grep -rn "checkConsistency" tests/ | wc -l
```
→ 775 hits across 14 test files (quoted from the run); `grep -n "guideSnaps" src/` → timelinemodel.hpp:1062 (default {}), timelinemodel.cpp:6727/6791, plus three friend declarations.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "kdenlive", query: "checkConsistency snap map rebuild remaining_compo field walk", limit: 10, fields: ["signature", "name", "file"] });
```
(Graph MCP was not connected in the authoring session; the grep probe above was executed byte-for-byte instead.)

## Verdict
Adopt the recompute-and-compare architecture: rebuild every derived structure from primary state and diff against the live one, with a named warning per drift class; adopt the two-directional cross-model registration check and the set-difference render-graph reconciliation with explicit artifact skips. Adapt the specific passes to your model's derived structures (snap grids, external registries, planted render nodes). Omit the MLT field-walk mechanics if your renderer has no service chain — but keep an equivalent planted-vs-recorded reconciliation. State the caveat: the prover is test-oracle infrastructure, not a runtime guard; it is not called on the hot path in production code.
