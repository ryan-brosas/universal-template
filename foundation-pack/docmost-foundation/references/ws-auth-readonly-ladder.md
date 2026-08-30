<!-- capsule-v2 -->
# WS auth + readOnly ladder — who may open a collab socket, and when is it forced read-only?

**Source:** docmost AGPL-3.0 `main@549cf7c0053bb4f4c3c4e08d588b1f0c69297daf`; Codebase Memory `ext-docmost`. **Question:** What is the exact decision ladder from a collab JWT to an editable vs read-only Yjs connection, including page-tree restrictions and deleted pages?

## AuthenticationExtension.onAuthenticate
**Path/Symbol:** `apps/server/src/collaboration/extensions/authentication.extension.ts`:`onAuthenticate` (lines 31–109).
**Signature:** `onAuthenticate(data: onAuthenticatePayload): Promise<{ user: User }>`; documentName format `<something>.<pageId>` parsed by `getPageId = (name) => name.split('.')[1]`.
**Data Shape:** Input token is a **dedicated short-lived `JwtType.COLLAB` JWT** — not the main session token. Output mutates only `data.connectionConfig.readOnly`. Denials throw `UnauthorizedException`/`NotFoundException`.

### Decisive source
```ts
if (hasAnyRestriction) {
  if (!canAccess) { throw new UnauthorizedException(); }
  if (!canEdit)   { data.connectionConfig.readOnly = true; }   // restricted page, reader-level
} else {
  // No restrictions - use space-level permissions
  if (userSpaceRole === SpaceRole.READER) {
    data.connectionConfig.readOnly = true;
  }
}
if (page.deletedAt) {
  data.connectionConfig.readOnly = true;                        // trashed pages stay readable
}
```

**Flow:** verify COLLAB JWT → load user (reject disabled) → load page → space roles via `getUserSpaceRoles` + `findHighestUserSpaceRole` (no role ⇒ deny) → page-tree check via `canUserEditPage` → apply the ladder above → return `{user}` as connection context.
**Invariant:** readOnly is a *connection* property set once at auth time, enforced downstream by hocuspocus — the extension never edits the doc to enforce it. Deleted pages remain viewable. Page-level restriction overrides space role entirely (`hasAnyRestriction` branch), so a workspace-writer on a restricted-reader page still gets readOnly. The collab token is a distinct audience: reuse of the app JWT here must fail.
**Probe:** `grep -cF 'data.connectionConfig.readOnly = true' apps/server/src/collaboration/extensions/authentication.extension.ts` (=3) and `grep -cF 'JwtType.COLLAB' apps/server/src/collaboration/extensions/authentication.extension.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-docmost", query: "AuthenticationExtension onAuthenticate readonly connectionConfig", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder order (deny → readOnly-restricted → space-role readOnly → deleted-page readOnly) and the dedicated-token pattern; adapt the role enum and repo calls; omit Nest guard plumbing. Direct tests: none for this extension upstream (token.service.spec.ts covers the JWT layer); coverage caveat recorded.
