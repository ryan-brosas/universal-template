<!-- capsule-v2 -->
# Mix metadata — how do you keep mix geometry honest after arbitrary moves/resizes without storing redundant positions?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter stores mixes as transitions between two sub-playlists but must answer "what are the current in/out of this mix?" after any move/resize, detect orphaned mixes whose partner clip was deleted, and collapse zero-length mixes — without a second source of truth that drifts.

## Derived MixInfo + post-mutation syncronizeMixes reconciliation
**Path/Symbol:** `src/timeline2/model/trackmodel.hpp:class MixInfo` (26–38); `src/timeline2/model/trackmodel.cpp:TrackModel::getMixInfo` (2244–2295), `syncronizeMixes` (2518–2570), `getMixTracks` (2759–2765), `getMixParams` (2767–2773), `hasStartMix/hasEndMix/isOnCut/getSecondMixPartner` (2578–2629); reconciliation call sites `timelinemodel.cpp:3495, 3833, 4658, 4716, 4771, 4797`.
**Signature:** `std::pair<MixInfo,MixInfo> getMixInfo(int clipId) const` / `void syncronizeMixes(bool finalMove)` / `std::pair<int,int> getMixTracks(int cid) const`.
**Data Shape:** `MixInfo { int firstClipId=-1; int secondClipId=-1; std::pair<int,int> firstClipInOut={-1,-1}; std::pair<int,int> secondClipInOut={-1,-1}; int mixOffset=0; }` — ALL fields derived at read time from `m_mixList`/`m_sameCompositions` + live clip positions; `-1` is the "no mix / partner deleted" sentinel.

### Decisive source
```cpp
// trackmodel.cpp:2518-2558 — syncronizeMixes recomputes every mix window from ground truth
void TrackModel::syncronizeMixes(bool finalMove)
{
    QList<int> toDelete;
    for (const auto &n : m_sameCompositions) {
        int secondClipId = n.first;
        int firstClip = m_mixList.key(secondClipId, -1);
        Q_ASSERT(firstClip > -1);
        if (m_allClips.find(firstClip) == m_allClips.end() || m_allClips.find(secondClipId) == m_allClips.end()) {
            // One of the clip was removed, delete the mix
            Mlt::Transition &transition = *static_cast<Mlt::Transition *>(m_sameCompositions[secondClipId]->getAsset());
            QScopedPointer<Mlt::Field> field(m_track->field());
            field->lock(); field->disconnect_service(transition); field->unlock();
            toDelete << secondClipId; m_mixList.remove(firstClip); continue;
        }
        // Asjust mix in/out
        int mixIn  = m_allClips[secondClipId]->getPosition();
        int mixOut = m_allClips[firstClip]->getPosition() + m_allClips[firstClip]->getPlaytime();
        if (mixOut <= mixIn) {
            if (finalMove) { mixOut = mixIn; }   // committed move: zero-length mix dies
            else           { mixOut = mixIn + 1; } // mid-drag: keep a 1-frame stub so it can be restored
        }
        if (mixIn == mixOut) { /* disconnect + queue delete */ }
        else                 { transition.set_in_and_out(mixIn, mixOut); }
        ... setMixDuration(mixOut - mixIn) + dataChanged(MixRole, MixCutRole / MixEndDurationRole)
    }
    for (int i : toDelete) m_sameCompositions.erase(i);
}
```
```cpp
// trackmodel.cpp:2244-2293 — getMixInfo derives BOTH sides live; deleted partner => sentinel
if (m_sameCompositions.count(clipId) > 0) {          // mix at clip START
    startMix.firstClipId = m_mixList.key(clipId, -1);
    startMix.secondClipId = clipId;
    if (ptr->isClip(startMix.firstClipId)) { /* fill InOut from live position+playtime */ }
    else { startMix.firstClipId = -1; }           // Clip was deleted
}
int secondClip = m_mixList.value(clipId, -1);        // mix at clip END
...
```

**Flow:** writes go through requestClipMix (see mix-plant-replant-ladder) which plants the transition with an initial window; afterwards NOTHING stores mix geometry — `getMixInfo` re-derives both clips' in/out from their current positions on every read, and `syncronizeMixes(finalMove)` runs as a RECONCILIATION pass after every move/resize operation family (call sites above): orphaned mixes (either partner id missing from `m_allClips`) are disconnected under a field lock and removed from both registries; surviving mixes get `set_in_and_out(mixIn, mixOut)` from live positions; a non-positive overlap becomes a 1-frame stub during drags (`finalMove=false`) so the user can drag back, but collapses to zero and deletes on commit (`finalMove=true`). `getMixTracks` reads the `a_track`/`b_track` ints stored ON the transition asset itself; `getMixParams` returns assetId + parameter list for cloning; `isOnCut(cid)` finds the exact cut frame between two unmixed neighbors (±1 snapping tolerance) or -1.
**Invariant:** exactly one source of truth for mix geometry = clip positions; registries hold only identity (which clips, which asset); both registries change together (`mixCount()` asserts equal sizes); a mix can never outlive its partner clips — reconciliation deletes it rather than leaving a dangling transition; mid-drag state may carry 1-frame stubs, committed state never does.
**Probe:** `tests/mixtest.cpp:212-234` "Add mix and resize last clip in playlist": resizing a mixed clip changes playtime 33→60 and undo restores 33 — the mix window follows the resize via synchronization; `tests/mixtest.cpp:177-210` cut sections show registry integrity across cuts (playlist indices pinned per side); `tests/timewarptest.cpp` exercises the same delete/replant path that triggers reconciliation for speed changes.

## Get live surrounding code
**Retrieve:**
```bash
$ grep -n 'getMixInfo\|syncronizeMixes\|getMixTracks\|getMixParams' src/timeline2/model/trackmodel.cpp
2244:std::pair<MixInfo, MixInfo> TrackModel::getMixInfo(int clipId) const
2518:void TrackModel::syncronizeMixes(bool finalMove)
2759:std::pair<int, int> TrackModel::getMixTracks(int cid) const
2767:std::pair<QString, QVector<QPair<QString, QVariant>>> TrackModel::getMixParams(int cid)
$ grep -n 'class MixInfo' src/timeline2/model/trackmodel.hpp
26:class MixInfo
$ grep -n 'syncronizeMixes' src/timeline2/model/timelinemodel.cpp
3495:            getTrackById_const(tid)->syncronizeMixes(finalMove);
3833:                getTrackById_const(tid)->syncronizeMixes(true);
4658:                        getTrackById_const(tid)->syncronizeMixes(true);
4716:                                    getTrackById_const(trackId)->syncronizeMixes(true);
4771:                                getTrackById_const(trackId)->syncronizeMixes(true);
4797:                getTrackById_const(t)->syncronizeMixes(true);
# executed live this pass; graph search_graph unavailable (MCP not connected in session)
```

## Verdict
Adopt derive-don't-store: keep only identity registries and recompute geometry from item positions on read; run one reconciliation pass after each mutation family with a two-mode collapse policy (stub during interaction, delete on commit). Adopt the -1 sentinel convention for "partner gone" instead of exceptions. Adapt the field lock/unlock around `disconnect_service` to your host's compositor transaction; omit `isOnCut` unless you port the "mix at cursor" affordance. This pattern generalizes to ANY pairwise overlay (crossfades, LUT blends, audio ducking pairs) over a linear document.
