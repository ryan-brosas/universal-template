<!-- capsule-v2 -->
# Raw-op publication ladder — how do evaluated rows become ShareDB ops without touching the database?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How are computed cell values published as ops with correct versions and null semantics?

## publishBatch / buildEvaluatedRows
**Path/Symbol:** `apps/nestjs-backend/src/features/record/computed/services/computed-evaluator.service.ts:publishBatch` (:350–401), `buildEvaluatedRows` (:317–348).
**Signature:** `publishBatch(tableId, impactedFieldIds, validFieldIds, excludeFieldIds, evaluatedRows): number`; rows `{recordId, version, prevVersion?, fields}`.

### Decisive source
```ts
const hasValue = Object.prototype.hasOwnProperty.call(fields, fid);
const newCellValue = hasValue ? fields[fid] : null;
return RecordOpBuilder.editor.setRecord.build({ fieldId: fid, newCellValue, oldCellValue: null }); // :373–379
...
const opVersion = prevVersion ?? version;                                                        // :385
this.batchService.saveRawOps(tableId, RawOpType.Edit, IdPrefix.Record,
  opDataList.map(({ docId, version, data }) => ({ docId, version, data })));                     // :393–398
```

**Flow:** RETURNING row → per-field `convertDBValue2CellValue` (generated formula columns swap to their generated name first, :333–340) → null-valued cells DROPPED from map (:343) → publish step reconstructs absence as explicit NULL ops via `hasOwnProperty` (distinguishes "evaluated to null" from "field not projected"); `oldCellValue:null` always (computed values are not diffed against old — clients receive authoritative state); op version prefers `__prev_version` (pre-update snapshot captured by the UPDATE...RETURNING) so ShareDB sees the pre-existing version.
**Invariant:** Absent-vs-null distinction is structural: dropping the key means "not projected"; publishing must NOT silently skip null results or stale cells linger client-side. Ops are RAW — no DB write, no version bump here (flush post-commit elsewhere).
**Probe:** exercised via evaluator spec mock rows carrying `__prev_version` (:67–76); needles verified at pin (:385 `prevVersion ?? version`, :393 saveRawOps); graph retrieval `publishBatch` resolves :350–401.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "saveRawOps", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt hasOwnProperty null reconstruction + prevVersion preference + raw-op doctrine; adapt RecordOpBuilder to your op format; omit batch-service indirection if you flush inline.
