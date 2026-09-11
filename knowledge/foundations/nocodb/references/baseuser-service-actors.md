<!-- capsule-v2 -->
|# Service-user synthesis — constant system actors appended outside the cache, visible to validators only

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** How do you make field validators accept system-stamped actors (anonymous/system/automation) that have no nc_users row — without polluting member pickers or the canonical cache?

## Path/Symbol
`packages/nocodb/src/models/BaseUser.ts:getUsersList` internal-user block (326–345); consumers: BaseModelSqlv2 User-field validator; export path export.service.ts:229-239 (getUserEmails).

**Signature:** opt-in flag `include_internal_user = false` on getUsersList.

**Data Shape:** appends one object per NOCO_SERVICE_USERS value: `{...u, deleted: true, meta: {icon: 'nocodb1', iconType: IconType.ICON}}`. IDs are SDK constants (`usranonymous`, …) that never exist in nc_users/nc_workspace_user.

### Decisive source
```ts
// Mirror the EE override (src/ee/models/BaseUser.ts): append service users
// ... so without this any caller validating a value against the returned
// list — e.g. the User/CreatedBy/LastModifiedBy field validator in
// BaseModelSqlv2 — would 422 on system-stamped actors like `usranonymous`
// from public shared-form submissions.
if (include_internal_user) {
  baseUsers.push(...Object.values(NOCO_SERVICE_USERS).map((u: any) => ({
    ...u,
    deleted: true,   // pickers filter !deleted; validators match by id
    meta: { icon: 'nocodb1', iconType: IconType.ICON },
  })));
}
```

**Flow:** caller needs reference-validation (field validator) or id→email map building → opts in → synthesized rows ride the SAME return shape as DB rows → UI surfaces filtering `!deleted` never show them; anything matching by id/email succeeds.

**Invariant:** (1) The `deleted:true` mark IS the visibility contract — one flag splits "validatable" from "pickable". (2) Synthesis happens AFTER the setList write-back (appended entries are NOT cached): constants stay out of the canonical cache. (3) CE mirrors an EE override deliberately so both editions validate identically. (4) Brand-marked meta keeps them renderable if ever surfaced.

**Probe:** no unit test upstream. Source-grounded probe: BaseUser.ts:326-345 comment + body verbatim, :334-335 ("they DO satisfy reference lookups by id"), consumer export.service.ts:229-239; pairing capsules baseuser-service-actors.md (superseded detail view), export-users-roster.md, cache-setlist-projection.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "include_internal_user NOCO_SERVICE_USERS NOCO_SERVICE_USERS deleted", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt constant-actor synthesis with the deleted-flag split and post-cache append; adapt actor ids/icons; omit unless host has system-stamped writes. Coverage caveat: no in-repo unit tests; source-grounded.
