<!-- capsule-v2 -->
# SSO-aware API token scoping — how do personal tokens differ for SSO users, and what does the delete path hide?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How does token listing/creation branch on SSO identity, and why is the base-scoped token's base_id nullability load-bearing?

## ApiTokensService
**Path/Symbol:** `packages/nocodb/src/services/api-tokens.service.ts` WHOLE (83L) — apiTokenList (:14-26), apiTokenCreate (:27-56), apiTokenDelete (:57-75).
**Signature:** list reads `(req.user as any)?.extra?.sso_client_id`; create stamps `fk_sso_client_id: ssoClientId || null` and `base_id: param.baseId ?? null`.
**Data Shape:** Token row carries `{description, fk_user_id, fk_sso_client_id?, base_id?}` — base_id null ⇒ account-wide token (org-tokens.controller path), set ⇒ confined to that base.

### Decisive source
```ts
async apiTokenList(param: { userId: string; req: NcRequest }) {
  // Check if user logged in via SSO
  const ssoClientId = (param.req.user as any)?.extra?.sso_client_id;
  if (ssoClientId) {
    // User logged in via SSO - show both SSO and normal tokens
    return await ApiToken.list(param.userId);
  } else {
    // User logged in normally - only show non-SSO tokens
    return await ApiToken.listForNonSsoUser(param.userId);
  }
}
```
```ts
const apiToken = await ApiToken.get(param.tokenId);
if (!apiToken) { NcError.notFound('Token not found'); }
if (
  !extractRolesObj(param.user.roles)[OrgUserRoles.SUPER_ADMIN] &&
  apiToken.fk_user_id !== param.user.id
) {
  NcError.notFound('Token not found');   // ownership violation masquerades as missing
}
```

**Flow:** list: SSO identity ⇒ both token families visible; normal user ⇒ non-SSO lister (an SSO-bound token must not authenticate a password session and vice versa). create: swagger validatePayload → trim description → stamp sso client + base confinement → appHooks emit. delete: fetch → **notFound for BOTH missing and foreign-owned tokens** (no existence oracle across users) unless SUPER_ADMIN → emit → delete.
**Invariant:** The dual notFound is deliberate: distinguishing "exists but not yours" would leak token inventory. The `base_id ?? null` comment pins the coupling — org-level creation leaves it undefined so the column default (null) marks account-wide scope; changing the default silently re-scopes every org token.
**Probe:** No runner at this pin — deterministic probes: search_graph resolves ApiTokensService methods; grep confirms exactly one `listForNonSsoUser` call site and one SUPER_ADMIN bypass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "ApiTokensService sso_client_id listForNonSsoUser", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt SSO-identity branching on token families and uniform notFound on foreign-token access. Adapt role vocabulary to your authz model. Omit the base-confinement column if your tokens are single-scope.
