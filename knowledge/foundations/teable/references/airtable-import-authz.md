<!-- capsule-v2 -->
# Airtable import authz — how are stored integration credentials and write targets guarded?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What stops a scoped-down PAT from using (or probing) an owner's stored Airtable OAuth token, and which permission is checked against which resource before streaming starts?

## assertIntegrationScope + pre-stream validPermissions
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-import.controller.ts`:`assertIntegrationScope` (:56–66), `importStream` guard block (:95–113), `AIRTABLE_IMPORT_TOKEN_RESOLVER` contract in `airtable-token-resolver.ts` (:7–16).
**Signature:** `private async assertIntegrationScope(integrationId: string | undefined): Promise<void>`.
**Data Shape:** routes are `POST /api/base/import-airtable/analyze` and `/stream`, both `@TokenAccess()`; required permission branches on the target: existing base ⇒ `base|table_import` on THAT base; new base ⇒ `base|create` on the target space.

### Decisive source
```ts
/**
 * Stored integration credentials are guarded by the user|integrations scope
 * on /api/user-integrations; a PAT reaching these @TokenAccess routes with
 * an integrationId must carry that same scope or it could use (and probe)
 * the owner's stored Airtable OAuth token without ever being granted it.
 */
if (!scopes.includes('user|integrations')) {
  throw new ForbiddenException(
    'The access token requires the user|integrations scope to use a stored integration credential.'
  );
}
```
```ts
// Authorize the real write target before doing anything: importing into an
// existing base needs table-import rights on THAT base — not base|create on
// whatever space the caller passes — while creating a new base needs
// base|create on the target space. (validPermissions intersects token scopes.)
const targetResourceId = importAirtableRo.baseId ?? importAirtableRo.spaceId;
```

**Flow:** zod-validated body → concrete target resource derived (`baseId ?? spaceId`) with a keep-guard even though the schema makes it unreachable → `validPermissions(target, [action], accessTokenId)` BEFORE any side effect or SSE header → integration scope assertion → SSE stream opens (heartbeats, close-cleanup) → resolver-side isolation: the community edition has NO integration storage; enterprise supplies `IAirtableImportTokenResolver` as an OPTIONAL dependency whose contract REJECTS integrations belonging to another user; raw tokens bypass the resolver entirely.
**Invariant:** The permission target is always a real resource — never "whatever space the caller passed" when importing into an existing base. Stored credentials are never reachable by tokens lacking the same scope that guards their management surface. Token resolution happens server-side per request so OAuth tokens never travel through the browser.
**Probe:** `grep -cF "user|integrations" apps/nestjs-backend/src/features/airtable-import/airtable-import.controller.ts` returns 3; `grep -cF "base|table_import" ...` returns 1.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"assertIntegrationScope validPermissions AIRTABLE_IMPORT_TOKEN_RESOLVER","limit":5,"detail":"ids"}'
```

## Verdict
Adopt scope-parity guarding for stored third-party credentials and concrete-target authorization before streaming; adapt action names to host RBAC; omit teable's SSE framing if the host streams differently. Coverage caveat: none.
