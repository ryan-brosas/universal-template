<!-- capsule-v2 -->
# Fade registry plane — how does a string-prefix-derived fade classification stay honest across add/remove/load/undo, and how do fades follow clip geometry through resize?

**Source:** kdenlive GPL-3.0 `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (MCP not connected this session — direct source+test read fallback). **Question:** Which effects count as fades, who maintains that classification, and what exactly do the `_refout`/`_refin` filter properties remember?

## m_fadeIns / m_fadeOuts registries
**Path/Symbol:** `src/effects/effectstack/model/effectstackmodel.hpp:202-203` (`std::unordered_set<int> m_fadeIns; std::unordered_set<int> m_fadeOuts;`); registration `effectstackmodel.cpp:528-600` (appendEffect), :678-700 (copyEffect), :1360-1400 (import/load), :840-852 (doAppendEffect tail); erase `:229-260` (removeEffectWithUndo); snapshot `:151-193` (cleanup/active-effect reset); consumers `:854-1008` (adjustStackLength), `:1010-1132` (adjustFadeLength), `:1171-1263` (getFadeMethod/getFadePosition/removeFade).
**Signature:** `bool adjustStackLength(bool adjustFromEnd, int oldIn, int oldDuration, int newIn, int duration, int offset, Fun &undo, Fun &redo, bool logUndo)`; `bool adjustFadeLength(int duration, bool fromStart, bool audioFade, bool videoFade, bool logUndo)`.
**Data Shape:** The registries hold effect ROW ids, classified at every registration point by effect-id string prefix: `fadein*`/`fade_from_*` → m_fadeIns; `fadeout*`/`fade_to_*` → m_fadeOuts. There is no stored "fade" flag on the effect itself — the classification is re-derived from the prefix convention at each entry point.

### Decisive source
```cpp
// appendEffect registration — prefix classification + level/alpha coercion
if (effectId.startsWith(QLatin1String("fadein")) || effectId.startsWith(QLatin1String("fade_from_"))) {
    m_fadeIns.insert(effect->getId());
    int duration = effect->filter().get_length() - 1;
    effect->filter().set("in", currentIn);
    effect->filter().set("out", currentIn + duration);
    ...
} else if (effectId.startsWith(QLatin1String("fadeout")) || effectId.startsWith(QLatin1String("fade_to_"))) {
    m_fadeOuts.insert(effect->getId());
    int filterOut = pCore->getItemIn(m_ownerId) + pCore->getItemDuration(m_ownerId) - 1;
    effect->filter().set("in", filterOut - duration);
    effect->filter().set("out", filterOut);
```

```cpp
// adjustStackLength fade-in shrink — the _refout restore latch
int referenceEffectOut = effect->filter().get_int("_refout");
if (referenceEffectOut <= 0) {
    referenceEffectOut = oldEffectOut;
    effect->filter().set("_refout", referenceEffectOut);   // one-shot: remember pre-shrink length
}
...
Fun reverse = [effect, referenceEffectOut]() {
    effect->setParameter(QStringLiteral("out"), referenceEffectOut, true);
    effect->filter().set("_refout", nullptr);              // cleared on restore
    return true;
};
```

**Flow:** Registration (append/copy/import/load) classifies by prefix, re-anchors the filter's in/out to the clip edge, and coerces `level`/`alpha` keyframe strings ("0=0;-1=1" for fade-in, "0=1;-1=0" for fade-out, with a `getKeyframeType` modifier suffix interpolated) so the fade curve always spans the full filter → removal erases from BOTH sets and emits delta-counted role updates (FadeInRole/FadeOutRole only when the set changed size) → the cleanup/active-effect reset snapshots BOTH full sets BY VALUE into the undo lambda, so undo restores the exact pre-reset classification → clip resize calls `adjustStackLength`: the fade-in branch re-anchors in/out to the new clip start and shrinks the fade when the clip is now shorter, latching `_refout` on first shrink so a later grow restores the user's ORIGINAL fade length; the fade-out branch mirrors with `_refin`; non-fade effects fall through to `KeyframeModelList::resizeKeyframes` and then a RequiresInOut refit (clips) or out-refit (track owners) → user-driven fade edits call `adjustFadeLength`, which CREATES the fade effect if missing and re-anchors from the clip edge.
**Invariant:** The registry sets and the set of fade-prefixed effects in the stack never diverge (every mutation path updates both); fade geometry always hugs the owning clip's edges after any resize; `_refout`/`_refin` are write-once-until-restore latches (cleared with `set(..., nullptr)` in the reverse lambda) — a deliberate exception to kdenlive's derive-don't-store rule, justified because the pre-shrink length is NOT derivable after the shrink happened.
**Probe:** `grep -c "m_fadeIns\|m_fadeOuts" src/effects/effectstack/model/effectstackmodel.cpp` → 47 hit lines. Executed this session. Direct test: `tests/effectstest.cpp:70-102` — fade-in stays on the LEFT cut half (original rowCount 1, split 0), fade-out follows the RIGHT half (original 0, split 1): the side-ownership contract `cleanFadeEffects` implements, pinned end-to-end through the real cut path.

## Get live surrounding code
**Retrieve (graph MCP unavailable; executed deterministic grep substitute):**
```bash
grep -n "getFadePosition\|getFadeMethod\|removeFade" src/effects/effectstack/model/effectstackmodel.cpp
# → :858-859 (adjustStackLength census), :1171/:1221/:1248 (definitions)
```

## Verdict
Adopt the derived-classification discipline: a role derived from a naming convention must be re-derived at every entry point and snapshotted by value into undo lambdas — never stored as a flag that can go stale. Adopt the one-shot restore latch (`_refout`/`_refin`) for any "shrink is lossy, grow should restore" geometry. Adapt the MLT filter property names and the level/alpha keyframe-string format to your host. Omit the single-fade assumption in getFadePosition/getFadeMethod (they read only the FIRST registry member — a known limitation if you allow multiple fades). Coverage caveat: no test references adjustStackLength/adjustFadeLength/removeFade directly; only the cut side-ownership contract is test-pinned (effectstest.cpp:70-102).
