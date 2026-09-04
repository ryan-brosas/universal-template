<!-- capsule-v2 -->
# Merge-plan step naming — why is the durable step list derived from data, and what does skip-path durability buy?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** How do you structure a dynamic-length batch as QStash workflow steps so a mid-run death resumes without redoing or skipping enrollments?

## loadMergePlan + merge-enrollment-<id>: plan-as-data, per-item named steps, skip cache clear
**Path/Symbol:** `apps/web/app/(ee)/api/workflows/merge-partner-accounts/route.ts:loadMergePlan` (:247-348) and the step loop (:83-96).
**Signature:** `loadMergePlan({ sourceEmail, targetEmail }): Promise<MergePlan>` where `MergePlan = { proceed: false; reason } | { proceed: true; sourcePartnerId, targetPartnerId, sourceImage, sourceUserId, hasRewinds, orderedSourceEnrollmentIds, programIdsToTransfer }`.
**Data Shape:** `CACHE_KEY_PREFIX = "merge-partner-accounts"`; verification-cache key `merge-partner-accounts:<userId>` gates re-entry; email comparisons are CASE-INSENSITIVE (`toLowerCase()` both sides, :278/:282) even though Prisma lookups fetch by raw emails.

### Decisive source
```ts
// Overlaps first, then transfers (preserves the original processing order).
const orderedSourceEnrollmentIds = [
  ...overlappingEnrollments,
  ...transferEnrollments,
].map(({ id }) => id);
// Step 2: ... Each step re-fetches the live enrollment so it is safe to retry
// after a partial run.
for (const enrollmentId of orderedSourceEnrollmentIds) {
  await context.run(`merge-enrollment-${enrollmentId}`, async () => {
    return await mergeSingleEnrollment({ enrollmentId, ... });
  });
}
```
(:332-336 ordering; :83-95 dynamic steps)

**Flow:** resolve both accounts by email (0/1/2 found → proceed-false reasons; same-id → refuse) · partition source enrollments into overlapping (target already enrolled) vs transfer sets · ORDER overlaps FIRST · return plan from inside `context.run("load-merge-plan")` so the ORDER ITSELF is checkpointed · `!plan.proceed` ⇒ a SEPARATE durable step `clear-cache-after-skip` deletes the verification key so the user can retry (sendTokens refuses new merges while it's set) · one `merge-enrollment-${id}` step per enrollment · finalize-transfers → cleanup-source-account → send-merged-emails (idempotencyKey `merge-partner-accounts/${userId}`).
**Invariant:** (1) step names embed enrollment ids: completed steps' results are cached by name across retries, so each enrollment transfers at most once even across crash-resume — a porter who names steps generically ("merge-enrollment") replays ALL enrollments on retry; (2) the plan is computed ONCE and persisted in step output — later steps must not recompute ordering (source state has changed by then); (3) EVERY skip path still runs through a durable step so the cache-clear cannot be lost on a retry storm; (4) failureFunction ALSO clears the cache (alerting "Some enrollments may already be merged... manual cleanup may be required", :213) — the entry gate must never permanently lock a user out because of an infra failure.
**Probe:** `tests/workflows/merge-partner-accounts-workflow.test.ts` :128-156 pins first-trigger 200 / second-trigger 400 no-duplicate via the cache gate; deterministic probe: `grep -c 'merge-enrollment-' apps/web/app/\(ee\)/api/workflows/merge-partner-accounts/route.ts` = 2 (comment + template literal).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "loadMergePlan", limit: 5 });
// → dub.apps.web.app.(ee).api.workflows.merge-partner-accounts.route.loadMergePlan @ merge-partner-accounts/route.ts 247-348
```

## Verdict
Adopt plan-as-first-step-output with item-id-bearing step names for any dynamically-sized durable batch, plus explicit durable skip/cleanup steps and failureFunction cache amnesty. Adapt transport API (`context.run` semantics). Omit dub's email verification UI flow.
