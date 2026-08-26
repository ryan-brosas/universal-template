<!-- capsule-v2 -->
# API-key org-principal auth — how do MACHINE clients authenticate, and what principal do they receive?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** the same REST surface serves browser users and external integrators — how does an API key become a working security principal, and what entitlement applies?

## Raw-key lookup → org synthesis with SUPERADMIN role, billing-gated by env presence
**Path/Symbol:** `apps/backend/src/services/auth/public.auth.middleware.ts:PublicAuthMiddleware.use` (:9-36).
**Signature:** `async use(req: Request, res: Response, next: NextFunction)`.
**Data Shape:** `Authorization` header carries the RAW key (no Bearer scheme parsing). Success attaches `req.org = { ...org, users: [{ users: { role: 'SUPERADMIN' } }]` } — an organization principal whose synthetic member passes any role guard inside that org.

### Decisive source
```ts
const org = await this._organizationService.getOrgByApiKey(auth);
if (!org) return res.status(401).json({ msg: 'Invalid API key' });
if (!!process.env.STRIPE_SECRET_KEY && !org.subscription) {
  return res.status(401).json({ msg: 'No subscription found' });
}
req.org = { ...org, users: [{ users: { role: 'SUPERADMIN' } }] };
next();
// catch (err) { throw new HttpForbiddenException(); }
```

**Flow:** missing header → json 401 'No API Key found'; unknown key → 401 'Invalid API key'; entitlement gate fires ONLY when `STRIPE_SECRET_KEY` exists (hosted SaaS): missing subscription ⇒ 401 'No subscription found'; otherwise synthesize the SUPERADMIN-flavored org principal → next().
**Invariant:** self-hosted deployments (no billing env) have NO entitlement gate at all — the subscription check is existence-conditional, not value-conditional; machine principals are ORG-scoped (never a user), and the synthesized SUPERADMIN role means downstream role checks cannot distinguish API traffic from an org owner.
**Porter trap (source-confirmed):** asymmetric error surfaces — auth misses are json-401-with-return, but anything THROWN inside the try becomes 403 Forbidden; keep the two channels straight or clients will mis-classify failures.
**Probe:** no upstream tests exist. Deterministic pins (executed): `grep -n 'STRIPE_SECRET_KEY\|SUPERADMIN\|getOrgByApiKey' apps/backend/src/services/auth/public.auth.middleware.ts` → :17/:23/:31.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "getOrgByApiKey PublicAuthMiddleware", limit: 5 });
```

## Verdict
Adopt: key→organization lookup returning an org principal with a max-role synthetic member, and an entitlement gate that exists iff the billing integration is configured. Adapt header scheme (add Bearer parsing) and decide consciously whether role guards should treat API traffic as owner-equivalent. Omit Stripe specifics. Coverage caveat: no test runner upstream.