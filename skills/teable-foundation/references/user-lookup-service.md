<!-- capsule-v2 -->
# UserLookupService — identifier→user resolution across id/email/name

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does teable resolve a user cell's identifiers (id/email/name) to full user records with avatars?

## User lookup service
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/PostgresUserLookupService.ts` (whole file, 17-57).
**Signature:** `listUsersByIdentifiers(identifiers): Promise<Result<UserLookupRecord[], DomainError>>`.
**Data Shape:** dedupes+filter-Boolean identifiers; queries `users` selecting `id/name/email` with an OR of `id in / email in / name in`; maps to `{id, name, email, avatarUrl=buildUserAvatarUrl(id)}`.

### Decisive source
```ts
const rows = await this.db.selectFrom('users')
  .select(['id', 'name', 'email'])
  .where(eb => eb.or([eb('id','in',unique), eb('email','in',unique), eb('name','in',unique)]))
  .execute();
return ok(rows.map(row => ({ id: row.id, name: row.name, email: row.email ?? null,
  avatarUrl: buildUserAvatarUrl(row.id) })));
```

**Flow:** dedupe identifiers → empty→`ok([])` → OR-match across id/email/name → map rows with a canonical avatar URL. Errors become `domainError.infrastructure` (never thrown).

**Invariant:** A single identifier may match by id OR email OR name (one OR query, not three); empty input short-circuits to `[]`; avatar URLs are always derived from the user id via `buildUserAvatarUrl`.

**Probe:** `record/repository/PostgresUserLookupService.spec.ts` — pins the OR-match and mapping.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresUserLookupService listUsersByIdentifiers buildUserAvatarUrl", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-OR-match across id/email/name and the avatar derivation. Adapt the users table/columns. Omit nothing portable. Probes pinned to the real spec.
