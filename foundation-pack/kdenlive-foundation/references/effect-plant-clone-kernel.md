<!-- capsule-v2 -->
# Effect plant/clone kernel — how does one effect model row keep filters planted across a master service plus N mirror-child services?

**Source:** kdenlive GPL-3.0 `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (MCP not connected this session — direct source+test read fallback). **Question:** When an effect stack is attached to a clip that also has a mirror audio-track producer, who owns the second filter, how is disable state propagated, and how is teardown keyed?

## Plant/clone/unplant family
**Path/Symbol:** `src/effects/effectstack/model/effectitemmodel.cpp:EffectItemModel::plant / loadClone / plantClone / unplant / unplantClone` (:223-337) + `src/effects/effectstack/model/effectstackmodel.cpp:EffectStackModel::addService / loadService / removeService` (:64-96).
**Signature:** `void plantClone(const std::weak_ptr<Mlt::Service> &service, int target = -1)`; `void unplantClone(const std::weak_ptr<Mlt::Service> &service)`; `void addService(std::weak_ptr<Mlt::Service> service)`.
**Data Shape:** `m_childEffects: QMap<int, shared_ptr<EffectItemModel>>` keyed by the child service's `_childid` (lazily stamped `++m_childId` on first clone, stored back on the service). Master filter lives in the row itself (`filter()`); clones are separately constructed `EffectItemModel`s that are NOT rows of the stack model.

### Decisive source
```cpp
// plantClone — the clone is a fresh asset, not a shared filter
effect = EffectItemModel::construct(effectId, ptr2);
effect->setParameters(getAllParameters(), false);
if (disable || m_asset->get_int("disable") == 1) {
    effect->filter().set("disable", 1);
}
int childId = ptr->get_int("_childid");
if (childId == 0) {
    childId = ++m_childId;
    ptr->set("_childid", childId);
}
m_childEffects.insert(childId, effect);
int ret = ptr->attach(effect->filter());
if (ret == 0 && target > -1) {
    ptr->move_filter(ptr->count() - 1, target);
}
```

**Flow:** `addService` plants a clone of every row on the new child service → `plantClone` probes the target domain (`set.test_audio` / `set.test_image`), disables the clone when the target lacks the effect's domain or the master is disabled, copies `in`/`out` when `out > in`, keys the clone by `_childid`, attaches, and optionally `move_filter`s it to a requested position → `loadService` is the reload twin: when filter counts already match it calls `loadClone`, which ADOPTS an existing same-`kdenlive_id` filter from the service (marked `_kdenlive_processed = 1`) instead of attaching a new one; on mismatch it strips all `kdenlive_id`-bearing filters and falls back to `addService` → `removeService` matches services by `_childid` value (not pointer identity) and `unplantClone`s every row → `unplantClone` detaches BOTH the adopted master filter and the keyed clone, then `take()`s the map entry.
**Invariant:** One master filter per row on `m_masterService`; at most one clone per child service per row; the `m_childEffects` key set and the set of attached child filters never diverge (teardown is keyed, so a re-added service with the same `_childid` reuses the slot). Clone disable state is a snapshot at plant time — later master disable changes do NOT propagate to existing clones.
**Probe:** `grep -n "plantClone\|unplantClone\|checkLambdaOrder" src/effects/effectstack/model/effectstackmodel.cpp src/effects/effectstack/model/effectitemmodel.cpp` → 15 hit lines (7 in effectstackmodel.cpp: 70, 111, 1368, 1395, 1397, 1828, 1830, 1840; 8 in effectitemmodel.cpp: 251, 299, 310 + call sites). Executed this session; counts quoted.

## Get live surrounding code
**Retrieve (graph MCP unavailable; executed deterministic grep substitute):**
```bash
grep -n "loadClone\|_kdenlive_processed\|_childid" src/effects/effectstack/model/effectitemmodel.cpp
# → loadClone definition :223, _kdenlive_processed set :247, _childid stamp :279-282
```

## Verdict
Adopt the keyed-clone pattern: one authoritative filter plus per-consumer clones keyed by a stable consumer id, with adopt-on-reload (`loadClone`) to survive producer rebuilds. Adapt the MLT `attach`/`detach`/`move_filter` calls to your host's filter chain API. Omit the Qt model-row coupling and the `qDebug`+`Q_ASSERT` failure posture (fail loudly in dev, but return typed errors in production). Coverage caveat: no direct test file references plantClone/unplantClone (grep over tests/ = 0 files); behavior is pinned only through the effect-stack integration suites.
