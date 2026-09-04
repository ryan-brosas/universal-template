<!-- capsule-v2 -->
# Single/bulk record funnel — how does one endpoint serve both one row and an array of rows without divergent code paths?

**Source:** NocoDB Sustainable Use License `develop@f7513664f3f3b7286023a7e832a8333808f7557b`; Codebase Memory `nocodb`. **Question:** When porting the record CRUD service, how does dataInsert/dataUpdate/dataDelete unify single-row and bulk-row requests while keeping trace ops, payload limits, and return shapes correct?

## DataTableService.dataInsert / dataUpdate / dataDelete
**Path/Symbol:** `packages/nocodb/src/services/data-table.service.ts:dataInsert` (:153-205), `dataUpdate` (:243-296), `dataDelete` (:303-347), `extractIdObj` (:411-433).
**Signature:** `async dataInsert(context: NcContext, param: { modelId; viewId?; body: any; cookie; undo?; apiVersion?; internalFlags?: { allowSystemColumn?; skipHooks? }; req? })`.
**Data Shape:** `body` is EITHER one row object OR an array of row objects — the array-ness alone selects bulk mode. Returns `result` array for bulk, `result[0]` for single.

### Decisive source
```ts
// Defense in depth: the source-level read-only restriction is enforced by
// the ACL middleware, but re-assert it against the actually-resolved target
// source so a caller that reaches this service with a mismatched
// authorization context (e.g. via the internal batch envelope) still cannot
// write to a data-read-only source.
if (source.is_data_readonly) NcError.sourceDataReadOnly(source.alias);

const result = await baseModel.bulkInsert(
  Array.isArray(param.body) ? param.body : [param.body],
  {
    cookie: param.cookie,
    insertOneByOneAsFallback: true,
    isSingleRecordInsertion: !Array.isArray(param.body),
    typecast: (param.cookie?.query?.typecast ?? '') === 'true',
    undo: param.undo,
    allowSystemColumn: param.internalFlags?.allowSystemColumn,
    skip_hooks: param.internalFlags?.skipHooks,
  },
);
return Array.isArray(param.body) ? result : result[0];
```

**Flow:** validateV1V2DataPayloadLimit → getModelAndView (id/tenancy resolution) → [update/delete only: checkForDuplicateRow] → Source.get(model.source_id) → **re-assert `is_data_readonly` on the RESOLVED source** → getBaseModelSQL → wrap body in array → bulkInsert/bulkUpdate/bulkDelete with `isSingleRecord*` mirror flag → unwrap `[0]` for single.
- Trace op names are computed PER CALL from body shape: `@TraceCommand((_ctx, p) => Array.isArray(p?.body) ? OperationName.recordBulkInsert : OperationName.recordInsert)` — one decorated method emits either op.
- Update/delete pass `throwExceptionIfNotExist: true`; delete additionally takes `internalFlags.allowSystemColumn` (no skipHooks — deletes always run hooks).
- Update/delete return `extractIdObj`: per row `{[pkTitle]: row[pk.title] ?? row[pk.column_name] ?? row[pk.id]}` — a TRIPLE fallback because callers address pks by title, column_name, or column id interchangeably.

**Invariant:** The read-only re-assertion must happen AFTER `Source.get(context, model.source_id)` resolves the actual target source, not trust the caller-supplied context — the comment names the internal batch envelope as the bypass it closes. And every bulk-capable method must keep `isSingleRecordInsertion/Updation/Deletion === !Array.isArray(body)` in sync with the unwrap ternary, or hooks/audit fire with the wrong arity.
**Probe:** No runner at this pin (packages/nocodb/tests holds SQL fixtures only) — deterministic probes: `search_graph --query dataInsert` resolves `DataTableService.dataInsert` :153-205; grep the file for `is_data_readonly` shows the re-assert in insert/update/delete but NOT in read paths (dataList/dataRead/dataCount).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "dataInsert bulkInsert isSingleRecordInsertion", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the wrap-in-array → single bulk call → unwrap pattern, the resolved-source read-only re-assertion, the shape-derived trace op name, and the title/name/id pk fallback ladder. Adapt `NcError.sourceDataReadOnly` wording and `validateV1V2DataPayloadLimit` thresholds to host limits. Omit the Profiler.start/log/end instrumentation (host tracing concern). Coverage caveat: no unit tests at this pin; behavior pinned by direct line-range reads.
