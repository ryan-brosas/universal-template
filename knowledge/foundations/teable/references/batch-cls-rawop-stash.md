<!-- capsule-v2 -->
# CLS-deferred raw-op publication — why are ShareDB ops STASHED instead of sent during calculation writes?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does the v1 engine make DB updates and realtime ops atomic when it writes outside the request's ShareDB flow?

## saveRawOps + tx.rawOpMaps
**Path/Symbol:** `apps/nestjs-backend/src/features/calculation/batch.service.ts:saveRawOps` (:476–537); stash sites `:144` and CLS get/set `:530–532`.
**Signature:** `saveRawOps(collectionId, opType: RawOpType, docType: IdPrefix, dataList: {docId, version, data}[]): IRawOpMap`.
**Data Shape:** `IRawOp` shapes per opType: Create `{create:{type:'json0',data}, v}`, Edit `{op: IOtOperation[], v}`, Del `{del:true, v}`; envelope carries `src = cls.getId() || 'unknown'`, `seq: 1`, `m: {ts: Date.now()}`.

### Decisive source
```ts
const prevMap = this.cls.get('tx.rawOpMaps') || [];
prevMap.push(rawOpMap);
this.cls.set('tx.rawOpMaps', prevMap);
return rawOpMap;
```

**Flow:** Build raw ops keyed by collection (`${docType}_${collectionId}`) → PUSH into the ambient CLS transaction's `rawOpMaps` array → the transaction owner publishes them only after commit (recorded in the pack's raw-op-publication-ladder plane). Version comes from the row read at fetch time (`fetchRawData` selects `__id,__version,__last_modified_time,__last_modified_by`; missing record throws localized recordNotFound BEFORE any write).
**Invariant:** Ops must never bypass the CLS stash — direct submission would let clients observe changes that a later rollback reverts. Unknown RawOpType throws rather than defaulting (silent no-op publication is worse than failure).
**Probe:** `grep -cF 'tx.rawOpMaps' apps/nestjs-backend/src/features/calculation/batch.service.ts` → 2; `grep -cF "unknown raw op type" <same>` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "saveRawOps rawOpMaps deferred share db ops", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt transaction-scoped op deferral with explicit unknown-type throw; adapt to your OT/realtime transport; omit json0 specifics if your doc model differs.
