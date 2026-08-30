<!-- capsule-v2 -->
# Keyframe resize anchor ladder — how do keyframe lists re-anchor when the owning clip's in/out moves?

**Source:** kdenlive GPL-3.0 `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (MCP not connected this session — direct source+test read fallback). **Question:** When a clip with keyframable effects is resized, which keyframes move, which are dropped, and how does the endless-resize lane differ from the plain in-point lane?

## KeyframeModelList::resizeKeyframes
**Path/Symbol:** `src/assets/keyframes/model/keyframemodellist.cpp:KeyframeModelList::resizeKeyframes` (:783-895); sole production caller `src/effects/effectstack/model/effectstackmodel.cpp:954` (adjustStackLength non-fade branch).
**Signature:** `void resizeKeyframes(int oldIn, int oldOut, int in, int out, int offset, bool adjustFromEnd, Fun &undo, Fun &redo)`.
**Data Shape:** Operates on every parameter model in `m_parameters` (multi-parameter effects resize ALL their parameter curves in lockstep). All mutations go through per-parameter `moveKeyframe`/`addKeyframe`/`removeKeyframe` on the CALLER's undo/redo accumulators — the resize itself pushes no undo entry of its own.

### Decisive source
```cpp
// in-point lane: re-anchor the in keyframe, sweep everything before the new in
Keyframe kf = getKeyframe(old_in, &ok);
KeyframeType::KeyframeEnum type = kf.second;
getKeyframe(new_in, &ok2);
if (!ok2) {
    for (const auto &param : m_parameters) {
        QVariant value = param.second->getInterpolatedValue(new_in);
        param.second->addKeyframe(new_in, type, value, true, undo, redo);
    }
}
if (ok) {
    for (const auto &param : m_parameters) {
        param.second->removeKeyframe(old_in, undo, redo);
    }
}
// Remove all keyframes before in
...while (nextOk) { pos = kf.first; if (pos < new_in) { removeKeyframe(pos...); } else break; }
```

**Flow:** Three lanes elected by arguments — (1) `adjustFromEnd=false, offset != 0`: ENDLESS-RESIZE lane (clip grew/shrank without moving its content origin): shift every keyframe by `-new_in` so the curve stays glued to source frames, dropping keyframes that fall outside; (2) `adjustFromEnd=false, oldIn != in`: IN-POINT lane: add an interpolated keyframe at the new in carrying the OLD in-keyframe's type, remove the old in keyframe, then sweep-remove everything before the new in; (3) `adjustFromEnd=true`: OUT-POINT lane: if ONLY in/out keyframes exist (the previous keyframe before old_out IS the clip in), MOVE the out keyframe to the new out (cheap path, early return); otherwise add an interpolated keyframe at the new out and remove everything beyond it. Single-keyframe stacks are exempt (`!singleKeyframe()` gate on the out lane's add+remove block).
**Invariant:** The keyframe AT the anchor edge is preserved (re-created with interpolated value + original type when the edge moves); keyframes outside the new [in, out] window are removed, never silently clamped; the caller's undo/redo accumulators receive every primitive so the whole resize is one undo step. The curve's shape between surviving keyframes is untouched — resize re-anchors edges, it never rescales intermediate positions (that is what the endless-resize offset lane is for).
**Probe:** `grep -rn "resizeKeyframes" src/ --include=*.cpp --include=*.hpp` → 4 hits (keyframemodellist.cpp:783 definition, keyframemodellist.hpp:104 declaration, compositionmodel.cpp call, effectstackmodel.cpp:954 call). Executed this session. Direct test: `tests/keyframetest.cpp:63-266` pins the underlying keyframe algebra (add/remove/move + undo round-trips) that resizeKeyframes composes; NO dedicated resize section exists — evidence gap recorded.

## Get live surrounding code
**Retrieve (graph MCP unavailable; executed deterministic grep substitute):**
```bash
grep -n "singleKeyframe\|getInterpolatedValue" src/assets/keyframes/model/keyframemodellist.cpp | head
# → singleKeyframe gate :878, getInterpolatedValue anchor reads :827/:858/:884
```

## Verdict
Adopt the three-lane election (endless-resize shift vs in-anchor vs out-anchor) and the anchor-preservation rule: the keyframe at a moved edge is re-created from interpolation with its original type before the old one is removed. Adapt GenTime/fps plumbing and the multi-parameter lockstep iteration to your host's curve model. Omit the qDebug 2-keyframe diagnostic noise. Coverage caveat: resizeKeyframes itself has no direct test; its primitives are pinned by keyframetest.cpp:63-266 and its caller is exercised only through integration paths.
