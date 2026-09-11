<!-- capsule-v2 -->
# Public form insert — how does an UNAUTHENTICATED submission get attributed, scheduled, attachment-processed, and field-filtered?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** When the public controller runs no GlobalGuard, what must dataInsert do before nestedInsert so audits have an actor and only published fields persist?

## PublicDatasService.dataInsert
**Path/Symbol:** `packages/nocodb/src/services/public-datas.service.ts:dataInsert` (:677-824); bulk-entry cap (:47-70).
**Signature:** `async dataInsert(context, param: { sharedViewUuid; password?; body; files: any[]; siteUrl; req })` → baseModel.nestedInsert(insertObject, req, null).
**Data Shape:** `fields` = view.model.columns FILTERED to view-columns with show:true, keyed by column TITLE, values rebuilt as merged `new Column({...viewColumn, ...modelColumn})`. Attachments accumulate per title from multipart files AND url-upload entries.

### Decisive source
```ts
// Public form submissions are unauthenticated by design (the public
// controller runs no GlobalGuard), so req.user is empty and the resulting
// DATA_INSERT / nested DATA_LINK audits would have a NULL actor. Attribute
// them to the anonymous service user and stamp the shared view/form id so
// the submission stays traceable.
if (!param.req.user?.id) {
  param.req.user = { ...NOCO_SERVICE_USERS[ServiceUserType.ANONYMOUS_USER] } as NcRequest['user'];
}
param.req.ncSharedViewId = view.id;
```
```ts
// A public form submission may arrive without a `data` field (e.g. an
// attachment-only submission where the fields are sent as files, or an empty
// body). In that case `body` is null/undefined and Object.entries would throw
// ... Default to an empty object so the submission still proceeds via the
// attachment/nested link handling below.
if (!body || typeof body !== 'object') body = {};
const insertObject = Object.entries(body).reduce((obj, [key, val]) => {
  if (key in fields) obj[key] = val;      // <-- THE field gate
  return obj;
}, {});
```

**Flow:** view by UUID → FORM-only type check → checkViewBaseType → password verify → **FormView.validateFormScheduling** (started/expired windows) → anonymous actor substitution + ncSharedViewId stamp → source readonly re-check → build visible-fields map → parse string bodies → coerce missing body to {} → keep ONLY keys in fields → attachments: multipart files under `_fieldName[\d]` names (binary→utf8 decode, strip prefix/suffix) uploaded via attachmentsService.upload; body entries shaped `{url}` without `{file}` go through uploadViaURL and are UNSHIFTED ahead of file uploads → JSON.stringify attachment arrays into insertObject → nestedInsert.
**Invariant:** The `key in fields` filter is the ONLY write surface an anonymous caller gets — no allowlist merge means unpublished columns are silently dropped, not errored. Actor attribution must happen BEFORE any audit-emitting call (uploads included). Form scheduling gates BEFORE body parsing. The cap constant documents its coupling: MAX_PUBLIC_BULK_ENTRIES = max(200, defaultGroupByLimitConfig.limitGroup) because "raising NC_DB_QUERY_LIMIT_GROUP_BY_GROUP past the cap would 400 every shared-view request."
**Probe:** No runner at this pin — deterministic probes: search_graph resolves PublicDatasService methods; grep confirms exactly one ANONYMOUS_USER substitution site and one `ncSharedViewId` stamp in this file.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "dataInsert NOCO_SERVICE_USERS validateFormScheduling", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: actor-substitution before audits, scheduling-before-parse, visible-fields-only write gate, dual attachment ingestion with url-uploads ordered first. Adapt service-user identity + scheduling vocabulary to host. Omit the binary fieldname decoding if your multipart layer already delivers utf8 names.
