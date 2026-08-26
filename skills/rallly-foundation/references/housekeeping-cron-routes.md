<!-- capsule-v2 -->
# Housekeeping endpoint ladder — how are cron jobs exposed and bounded safely?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** How does a serverless app expose destructive maintenance tasks to an external scheduler without auth leaks or timeout kills?

## Hono bearer-auth housekeeping routes
**Path/Symbol:** `apps/web/src/app/api/house-keeping/[...method]/route.ts` (whole file, 203L): bearer guard (30–43), poll tasks (45–93), `removeDeletedUsers` reaper (109–163).
**Signature:** GET routes `/api/house-keeping/{auto-close-polls|delete-inactive-polls|remove-deleted-polls|remove-deleted-users|delete-orphaned-anonymous-users}`; `export const maxDuration = 300`.
**Data Shape:** CRON_SECRET bearer token; per-run caps REMOVE_DELETED_USERS_BATCH_SIZE=50, REMOVE_DELETED_USERS_MAX_PER_RUN=500; JSON summaries `{success, summary:{...counts}}`.

### Decisive source
```ts
app.use("*", async (c, next) => {
  if (process.env.CRON_SECRET) {
    return bearerAuth({ token: process.env.CRON_SECRET })(c, next);
  }
  logger.error("CRON_SECRET is not set in environment variables");
  return c.json({ error: "CRON_SECRET is not set in environment variables" }, 500);
});
```
```ts
while (deletedUsers + failedUserIds.length < REMOVE_DELETED_USERS_MAX_PER_RUN) {
  const users = await findUsersScheduledForRemoval({ cutoff, excludeUserIds: failedUserIds, limit: REMOVE_DELETED_USERS_BATCH_SIZE });
  if (users.length === 0) break;
  for (const user of users) {
    try {
      await cancelUserSubscriptions({ userId: user.id });   // Stripe first, defensive
      if (user.customerId) await deleteStripeCustomer({ customerId: user.customerId });
      await deletePostHogPerson({ distinctId: user.id });
      await hardDeleteUser({ userId: user.id });            // DB last
      trackSystemEvent({ event: "account_deletion_complete" }); // personless by design
    } catch (error) { failedUserIds.push(user.id); }        // retry next run
  }
}
```

**Flow:** external scheduler hits each route on its own cadence → bearer-auth gate → task runs → structured count summary logged + returned. The user-reaper orders EXTERNAL stores before the DB row so a failure leaves the user intact for retry; failed ids are excluded and the loop re-queries until the per-run cap, with backlog spilling to the next daily run instead of risking a mid-user function timeout.
**Invariant:** fail-closed on missing secret (500, not open access); deletion order is subscriptions→customer→analytics→DB; per-run bounds turn unbounded queues into steady-state drainers; every task is idempotent because it can be re-invoked arbitrarily.
**Probe:** deterministic grep anchors: `grep -cF 'CRON_SECRET' 'apps/web/src/app/api/house-keeping/[...method]/route.ts'` → 4; `grep -n 'maxDuration = 300' 'apps/web/src/app/api/house-keeping/[...method]/route.ts'` → line 97.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "house-keeping removeDeletedUsers bearerAuth", limit: 5 });
```

## Verdict
Adopt the guard + ordering + cap pattern verbatim; adapt Hono→your router; omit Stripe specifics. No direct test — this is glue code whose invariants live in comments.
