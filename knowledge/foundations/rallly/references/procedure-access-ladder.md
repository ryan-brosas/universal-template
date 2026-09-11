<!-- capsule-v2 -->
# Procedure access ladder — which tRPC procedure guards each mutation tier, and where does self-hosting bypass paywalls?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** What is the middleware chain from public to pro, and how do maintenance mode, stale sessions, and self-hosted tiers interact with it?

## trpc.ts procedure composition
**Path/Symbol:** `apps/web/src/trpc/trpc.ts` (whole file, 236L): `maintenanceGuard` (32–41), `mutationSessionGuard` (47–77), `possiblyPublicProcedure` (83–96), `requireUserMiddleware` (99–119), `privateProcedure` (121–134), `adminProcedure` (136–152), `spaceProcedure` (154–169), `proProcedure` (171–181), `spaceOwnerProcedure` (183–192), `createRateLimitMiddleware` (194–234).
**Signature:** composable tRPC middlewares; errorFormatter surfaces `AppError.cause.code` as `data.appError`.
**Data Shape:** ladder: public → possiblyPublic → private → space → pro → spaceOwner; rate limits keyed `${name}:${identifier}` via Upstash-style createRatelimit.

### Decisive source
```ts
// Reads trust the session (cookie cache) without hitting the database.
// Mutations verify the user still exists and run with a fresh DTO; if the
// user is gone, the session is revoked so the client can't keep bouncing
// between the login page and pages that require an account.
const mutationSessionGuard = t.middleware(async ({ ctx, type, next }) => {
  if (type !== "mutation" || !ctx.user) return next();
  const user = await prisma.user.findUnique({ where: { id: ctx.user.id } });
  if (!user) { /* signOut + UNAUTHORIZED w/ AppError INVALID_SESSION */ }
  return next({ ctx: { user: createUserDTO(user) } });
});
```
```ts
export const proProcedure = spaceProcedure.use(async ({ ctx, next }) => {
  if (!isSelfHosted && ctx.space.tier !== "pro") {
    throw new TRPCError({ code: "PAYMENT_REQUIRED", /* ... */ });
  }
  return next();
});
```

**Flow:** every procedure starts with maintenanceGuard → mutationSessionGuard; guest-capable mutations (make/close/markAsDeleted) use possiblyPublic gated by isQuickCreateEnabled for guests; requireUserMiddleware additionally rejects banned users; adminProcedure re-reads role from DB because the cookie cache can hold a stale role. Rate limits are per-procedure-name + caller identifier with headers echoed onto ctx.event.
**Invariant:** reads are cheap (cookie cache), writes are verified — deleting a user mid-session must surface UNAUTHORIZED on their very next mutation, not phantom writes; self-hosted installs bypass pro gating at BOTH proProcedure (`!isSelfHosted`) and membership resolution (`effectiveSpaceMemberWhere` returns bare userId when billing disabled), so a porter who copies the cloud checks verbatim locks self-hosters out of their own polls.
**Probe:** deterministic grep anchors: `grep -n 'isSelfHosted' apps/web/src/trpc/trpc.ts` → lines 8 (import) + 172 (proProcedure bypass); `grep -cF 'isSelfHosted' apps/web/src/trpc/trpc.ts` → 2; `grep -n 'stale' apps/web/src/trpc/trpc.ts` → line 137 comment.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "privateProcedure spaceProcedure proProcedure", limit: 5 });
```

## Verdict
Adopt the ladder order and read-cheap/write-verified split verbatim; adapt rate-limit backend + auth SDK; omit PostHog/Quick Create specifics. No direct unit test — composition is source-pinned only.
