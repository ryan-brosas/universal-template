<!-- capsule-v2 -->
|# User roster export payload — email-keyed roles with workspace_roles carry-through

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** How is a base's collaborator list serialized into a portable payload — and what's the deliberate asymmetry with the import side?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs/export-import/export.service.ts:ExportService.serializeUsers` (856–873); import stub `import.service.ts:importUsers` (94–105); query twin `models/BaseUser.ts:getUsersList` (229–363).

**Signature:** `serializeUsers(context, {baseId}): Promise<{email, display_name, base_role, workspace_role}[]>`.

**Data Shape:** 4 fields per user; `workspace_role` comes from the join column `workspace_roles` NOT present in the TS type (`(user as any).workspace_roles`). Import counterpart throws notImplemented — the payload is forward-compatible wire shape, not a restore path.

### Decisive source
```ts
const serializedUsers = users.map((user) => ({
  email: user.email,                 // identity-free: email is the cross-instance handle
  display_name: user.display_name,
  base_role: user.roles,
  workspace_role: (user as any).workspace_roles,
}));
```

**Flow:** Base.get (missing → NcError) → getUsersList (cache-first three-table join; see baseuser-roster-query.md) → project to the 4-field payload. Consumers of the same getUsersList include getUserEmails (:229-239), which builds id→email maps so permission subjects survive the instance hop by email.

**Invariant:** (1) Users are the ONLY exported entities keyed by identity-not-id: ids mean nothing cross-instance, email does. (2) The `(user as any)` cast marks a type-gap between model row and export shape — porters must keep BOTH role layers or workspace context silently drops. (3) Export-without-import for users is deliberate: inviting users on the target instance is a product decision, not a data gap to "fix". (4) Payload omits ids entirely — no idMap entry, no collision risk.

**Probe:** no unit test upstream. Source-grounded probe: export.service.ts:865-870 verbatim, :229-236 (email-map consumer comment), import.service.ts:94-105 (notImplemented stub).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "serializeUsers base_role workspace_role getUsersList", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt the email-keyed dual-role payload and export-without-import asymmetry; adapt role names; omit display_name handling unless hosting profiles. Coverage caveat: no in-repo unit tests; source-grounded.
