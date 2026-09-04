<!-- capsule-v2 -->
# Impact hint normalization — why do link-field updates get injected into valueFieldIds, and why does the planner need the split anyway?

## normalize = dedupe(value ∪ link into value, link); raw split preserved for before-image/extra-seed decisions
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `normalizeImpactHint(impact?)` (:3934–3957), consumers :2118/:2297/:2606/:2891/:3740; raw-split construction `updateMany` :2286–2296 and builder-emitted `impact` in updateOne (:2098–2115).
**Signature:** `(impact?: UpdateImpactHint): UpdateImpactHint | undefined` where `UpdateImpactHint = {valueFieldIds: FieldId[], linkFieldIds: FieldId[]}`.

### Decisive source
```ts
const valueFieldIds = new Map<string, core.FieldId>();
for (const fieldId of impact.valueFieldIds) valueFieldIds.set(fieldId.toString(), fieldId);
// Link value updates should propagate both link-relation and value semantics.
for (const fieldId of impact.linkFieldIds)  valueFieldIds.set(fieldId.toString(), fieldId);   // UNION
const linkFieldIds = new Map<string, core.FieldId>(...linkFieldIds only);
return { valueFieldIds: [...valueFieldIds.values()], linkFieldIds: [...linkFieldIds.values()] };
```

**Flow:** take the builder's RAW split (which fields held values vs which were links) → normalized.valueFieldIds := raw.value ∪ raw.link; normalized.linkFieldIds := raw.link → feed normalized into plan inputs so cross-record rollup/lookup propagation treats a changed link as BOTH a relation change and a value change.
**Invariant:** The DUPLICATION is deliberate: seed planning wants links counted as values (a re-linked row's foreign rollups must recompute), while before-image capture and extra-seed collection want to know WHICH fields are links (to load old link targets — see buildOldLinkExtraSeedRecords :931–962 which iterates raw link ids calling isOneWay()). Porters who collapse to one list lose either propagation (no union) or cheap link-specific handling (no split). Map-keyed dedup keeps id-string identity stable across repeated entries from multiple builders. undefined passes through untouched — callers treat absence as "nothing changed" short-circuit (:2886–2890).
**Probe:** deterministic grep :3943–3946 (union comment + loop).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "normalizeImpactHint UpdateImpactHint linkFieldIds", limit: 5 });
```
## Verdict
Adopt when derived-data planning and physical-link bookkeeping consume the same change set: keep the raw typed split, derive the planner view by unioning links into values at one named boundary.
