<!-- capsule-v2 -->
# Durable QStash workflow step contract — how do you structure a multi-step, retriable background workflow so a partial run can resume without double-applying?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1` (drift pass; file is new since `873edc5a`); Codebase Memory `dub`. **Question:** What are the rules for wrapping each unit of work in a durable workflow (`serve` + `context.run`) so retries resume cleanly?

## serve() step choreography in merge-partner-accounts
**Path/Symbol:** `apps/web/app/(ee)/api/workflows/merge-partner-accounts/route.ts:POST` (serve handler :49-190; options :191-245).
**Signature:** `export const { POST } = serve<Input>(async (context) => {...}, { initialPayloadParser, failureFunction })`.
**Data Shape:** `Input = { userId, sourceEmail, targetEmail }`; steps return plain JSON-serializable values that QStash persists as step output; `loadMergePlan` returns a discriminated `{ proceed: false, reason } | { proceed: true, ...plan }`.

### Decisive source
```ts
const plan = await context.run("load-merge-plan", async () => {
  return await loadMergePlan({ sourceEmail, targetEmail });
});
if (!plan.proceed) {
  await context.run("clear-cache-after-skip", async () => {
    await redis.del(`${CACHE_KEY_PREFIX}:${userId}`);
    return logAndReturn({ outputLog: `Cleared merge cache after skipped merge: ${plan.reason}` });
  });
  return;
}
for (const enrollmentId of orderedSourceEnrollmentIds) {
  await context.run(`merge-enrollment-${enrollmentId}`, async () => {
    return await mergeSingleEnrollment({ /* re-fetches live enrollment inside */ });
  });
}
```

**Flow:** five named steps — `load-merge-plan` → dynamic `merge-enrollment-<id>` per source enrollment (overlaps first) → `finalize-transfers` → `cleanup-source-account` (rewinds → user → fraud events → partner LAST) → `send-merged-emails` (cache clear + idempotency-keyed batch email). Each step's output is durably recorded by QStash; on retry only incomplete steps re-execute.
**Invariant:** every step body must be IDEMPOTENT because any step can re-run after a partial failure — `mergeSingleEnrollment` re-fetches the live enrollment and skips if it moved partners or vanished ("Enrollment X already on target partner, skipping"). The failureFunction clears the verification Redis cache on terminal failure so the user can restart from step 1, and its alert message explicitly warns "Some enrollments may already be merged … manual cleanup may be required". Step data must be JSON-serializable (plans/results cross process boundaries). Skip paths still go through `context.run` (the skip decision itself is durable).
**Probe:** `tests/workflows/merge-partner-accounts-workflow.test.ts` — first trigger 200 and merged links contain the source link (:128-134 region), second trigger returns 400 with NO duplicated links (:149-155), i.e. replaying a merge does not double-apply.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "serve load-merge-plan failureFunction", limit: 8 });
// → app.(ee).api.workflows.merge-partner-accounts.route.POST @ route.ts 49-245
```

## Verdict
Adopt the step contract: name every durable unit, make bodies idempotent + self-revalidating, keep payloads serializable, clear entry-gate caches in failureFunction. Adapt flow-control keys and step granularity to your queue. Omit QStash specifics when porting onto Temporal/Inngest — the contract transfers, the SDK does not.
