<!-- capsule-v2 -->
# record-crud-actor-and-error-envelope — How do tool-facing CRUD services standardize actor injection and error surfacing?

**Source:** twenty-crm (AGPL-3.0 — patterns only, never verbatim), main@a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0; Codebase Memory `ext-twenty-crm`. **Question:** What is the common create/upsert service contract (automation gate, actor metadata, error-to-result conversion, slim responses)?

## record-crud-actor-and-error-envelope
**Path/Symbol:** `packages/twenty-server/src/engine/core-modules/record-crud/services/create-record.service.ts:CreateRecordService.execute` (:26-110); twin `upsert-record.service.ts` (:24-87).
**Signature:** `execute(params: {objectName, objectRecord, authContext, rolePermissionConfig?, createdBy?, slimResponse?}): Promise<ToolOutput>` where `ToolOutput = {success, message, result?, recordReferences?, error?}`.
**Data Shape:** NEVER throws to the caller — every failure converts to `{success:false, message, error}`; success carries the processed record (or `{id}` when `slimResponse`) plus `recordReferences[{objectNameSingular, recordId, displayName}]`.

### Decisive source
```ts
const actorMetadata = params.createdBy ?? {
  source: FieldActorSource.WORKFLOW,
  name: 'Workflow',
};
const cleanedRecord = removeUndefinedFromRecord(objectRecord);
const dataWithActor = { ...cleanedRecord, createdBy: actorMetadata };
```
(:53-63 — explicit caller actor wins; otherwise a WORKFLOW default is stamped.)

**Flow:** build shared context via CommonApiContextBuilderService (metadata maps + selected fields + permissions) → gate on `canObjectBeManagedByAutomation({nameSingular})`, throwing RecordCrudException INVALID_REQUEST if the object forbids automation writes (:36-51) → strip undefined → inject `createdBy` → delegate to the common runner → wrap result. Error handling is two-tier: `RecordCrudException` ⇒ clean `{success:false, error: error.message}` without logging; anything else ⇒ `logger.error(...)` THEN the same envelope with a generic fallback string for non-Error throws (:69-86). Upsert differs only in passing `upsert:true` and skipping actor injection.
**Invariant:** the automation surface must never leak stack traces as exceptions — errors are DATA. The automation gate runs BEFORE any write attempt (deny early). `createdBy` is injected exactly once at this boundary; deeper layers treat it as system-owned.
**Probe:** `grep -c 'canObjectBeManagedByAutomation' packages/twenty-server/src/engine/core-modules/record-crud/services/create-record.service.ts packages/twenty-server/src/engine/core-modules/record-crud/services/upsert-record.service.ts` → 2 in each (import + gate call).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-twenty-crm", query: "CreateRecordService execute ToolOutput", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the error-as-data envelope + two-tier logging and the deny-early automation gate for any agent/tool-facing CRUD layer. Adapt actor-source enum values to your domain. Omit Twenty's ToolOutput type shape but keep recordReferences-style display resolution if your consumers render links.
