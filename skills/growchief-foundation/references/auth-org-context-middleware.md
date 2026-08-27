<!-- capsule-v2 -->
# Auth org-context middleware — how does ONE middleware hand every downstream handler a verified user AND an active organization without controllers touching auth?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** multi-tenant APIs need request-scoped {user, org} context incl. support impersonation — where is it resolved and what exactly is trusted?

## JWT verify → impersonate → activate-gate → org pick, all-or-401
**Path/Symbol:** `apps/backend/src/services/auth/auth.middleware.ts:AuthMiddleware.use` (:15-64) — fan-in 65 (hottest backend node).
**Signature:** `async use(req: Request, res: Response, next: NextFunction)` (NestMiddleware).
**Data Shape:** token = `req.headers.auth || req.cookies.auth`; org hint = `req.cookies.showorg || req.headers.showorg`; impersonation hint = `req.cookies.viewas`. Attaches `req.user` (User with password field DELETED) and `req.org` (organization row).

### Decisive source
```ts
user = EncryptionService.verifyJWT(auth) as User | null;
let orgHeader = req.cookies.showorg || req.headers.showorg;
if (user?.isSuperAdmin && req.cookies.viewas) {
  const orgUser = await this._userService.getOrgUser(req.cookies.viewas);
  if (orgUser) { user = orgUser.user; user.isSuperAdmin = true;
    user.viewas = req.cookies.viewas; orgHeader = orgUser.organizationId; }
}
if (!user || !user.activated) throw new HttpUnauthorized();
delete user.password;
const organization = (await this._organizationService.getOrgsByUserId(user.id))
  .filter((f) => !f.users[0].disabled);
const setOrg = organization.find((org) => org.id === orgHeader) || organization[0];
req.user = user; req.org = setOrg;
// catch (err) { throw new HttpUnauthorized(); }
```

**Flow:** verify JWT → superadmin-only impersonation swap (viewas cookie selects the target org-user; isSuperAdmin flag PRESERVED onto the swapped user so nested checks still see admin) → activated gate → strip password before attachment → resolve ALL org memberships fresh from DB filtered to non-disabled → prefer the showorg hint, else fall back to FIRST membership → attach both and continue.
**Invariant:** every failure funnels into ONE broad catch throwing 401 — partially-resolved context can never reach a handler; the active org is re-derived FROM THE DATABASE per request, never trusted from token claims (membership revocation takes effect immediately).
**Porter trap (source-confirmed):** the late guard `if (!organization)` is DEAD CODE — an array from `.filter()` is always truthy, so zero-enabled-orgs yields `req.org = undefined` (via the `organization[0]` fallback), not a 401. Reproduce deliberately or fix explicitly; do not copy blindly.
**Probe:** no upstream tests exist. Deterministic pins (executed): `grep -n 'viewas\|showorg\|delete user.password\|user.activated' apps/backend/src/services/auth/auth.middleware.ts` → :23/:24/:25/:30/:39/:44.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "AuthMiddleware verifyJWT showorg", limit: 5 });
```

## Verdict
Adopt: single choke-point middleware resolving {user, active-org} per request from DB with broad-catch 401 semantics and explicit impersonation preservation. Adapt cookie/header names and your membership filter. Omit the dead empty-array guard (or fix it). Coverage caveat: no test runner upstream; coverage check no_recorded_issue.
