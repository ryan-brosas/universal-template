<!-- capsule-v2 -->
# Effect ordering check-lambda — how is the "built-ins first, flip on top" ordering invariant enforced as part of the undoable operation?

**Source:** kdenlive GPL-3.0 `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (MCP not connected this session — direct source+test read fallback). **Question:** After an effect is added, copied, or imported, what repairs its row position, and why is that repair a lambda instead of an immediate move?

## checkLambdaOrder
**Path/Symbol:** `src/effects/effectstack/model/effectstackmodel.cpp:EffectStackModel::checkLambdaOrder` (:2254-2288).
**Signature:** `Fun checkLambdaOrder(const std::shared_ptr<EffectItemModel> &effect)`.
**Data Shape:** Returns a `Fun` (`std::function<bool(void)>`): either a no-op (`[]() { return true; }`) or a `moveItem_lambda(effect->getId(), targetRow, false)`. Composed into the CALLER's `local_redo` via `PUSH_LAMBDA`, so the ordering fix is part of the same undoable operation.

### Decisive source
```cpp
if (effect->isBuiltIn()) {
    int row = rowCount() - 1;
    if (row >= 0) {
        if (effect->getAssetId().contains(QLatin1String("flip"))) {
            // Flip effect, must go on top
            sub = moveItem_lambda(effect->getId(), 0, false);
            return sub;
        } else {
            int i = 0;
            for (; i < row; i++) {
                auto item = getEffectStackRow(i);
                if (!item) break;
                if (!std::static_pointer_cast<EffectItemModel>(item)->isBuiltIn()) break;
            }
            if (i < row) {
                // Built in effect must go before others
                sub = moveItem_lambda(effect->getId(), i, false);
                return sub;
            }
        }
    }
}
return sub;
```

**Flow:** Every registration path (appendEffect :580, copyEffect :699, importEffects :793, and the JSON/load path :1577, :2186, :2214) calls `checkLambdaOrder(effect)` right after `UPDATE_UNDO_REDO` folds the add into the caller's accumulators → the returned lambda is executed once immediately AND pushed onto `local_redo`, so redo replays the ordering fix → the scan finds the first non-built-in row and moves the new built-in just before it; "flip" always goes to row 0 because MLT evaluates filters top-down and flip must wrap the whole chain.
**Invariant:** Built-in effects always occupy a prefix of the stack; "flip" is always row 0. The invariant is repaired INSIDE the redo lambda, so undo/redo can never leave a half-ordered stack. Manual `moveEffect` refuses to move an effect before a built-in when built-in effects are enabled (:1275-1285), closing the loop from the other side.
**Probe:** `grep -n "checkLambdaOrder" src/effects/effectstack/model/effectstackmodel.cpp` → 7 hits (:580, :699, :793, :1577, :2186, :2214, definition :2254). Executed this session.

## Get live surrounding code
**Retrieve (graph MCP unavailable; executed deterministic grep substitute):**
```bash
grep -n "isBuiltIn" src/effects/effectstack/model/effectstackmodel.cpp
# → checkLambdaOrder scan :2269/:2272, moveEffect guard :1277, removeEffectWithUndo skip :229
```

## Verdict
Adopt the shape: ordering constraints enforced by a repair lambda composed into the same undoable operation, never as a separate post-pass (a post-pass would break undo determinism). Adapt the specific ordering rule (built-ins prefix, flip-first) to your host's filter semantics — the portable idea is "constraint repair lives in the redo path". Omit the string-contains("flip") special case unless your host has the same wrap-around filter. Coverage caveat: no direct test file references checkLambdaOrder (grep over tests/ = 0 files); the ordering invariant is pinned only indirectly through effect-stack integration tests.
