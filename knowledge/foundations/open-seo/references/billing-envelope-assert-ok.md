<!-- capsule-v2 -->
# Billing envelope / assertOk — how do you classify a vendor's status codes so access failures, empty successes, and charged failures each take the right branch?

**Source:** OpenSEO MIT `main@cd6a7820`; Codebase Memory `ext-open-seo`. **Question:** What is the shared status/billing ladder every DataForSEO endpoint goes through?

## assertOk ladder + task-status predicates
**Path/Symbol:** `src/server/lib/dataforseo/envelope.ts:assertOk` (:156-203), `DataforseoChargedTaskError` (:28-43), `isNoResultsTask` (:120-124), `isTaskInProgress` (:130-135), `describeInvalidField` (:101-112).
**Signature:** `function assertOk<T extends DataforseoTaskLike>(response: DataforseoResponseLike<T> | null, options: AssertOkOptions = {}): T` with options `{ classify?, classifyPath?, treatNoResultsAsEmpty?, okTaskStatusCode? }`.
**Data Shape:** Vendor response: top-level `status_code/status_message` + `tasks[0]` carrying its own codes and optional billing metadata (`path[]`, `cost`, `result_count`). Task-in-progress codes: `{20100, 40601, 40602}`.

### Decisive source
```ts
if (response.status_code !== 20000) {
  const message = response.status_message || "DataForSEO request failed";
  throw classify?.(response.status_code, message, classifyPath ?? "") ?? new AppError("INTERNAL_ERROR", message);
}
const task = response.tasks?.[0];
if (task.status_code !== (okTaskStatusCode ?? 20000)) {
  if (treatNoResultsAsEmpty && isNoResultsTask(task)) return task;   // 40501 empty success
  const classified = classify?.(task.status_code, message, path);
  if (classified) throw classified;                                   // access/balance FIRST
  if (billing = tryBuildTaskBilling(task))                            // then charged failure
    throw new DataforseoChargedTaskError(detailedMessage, billing, INVALID_FIELD_RE.test(message));
  throw new AppError("INTERNAL_ERROR", detailedMessage);
}
```

**Flow:** null response ⇒ INTERNAL_ERROR → top-level code ≠20000 ⇒ classifier or plain AppError → first task extracted → task code mismatch: no-results opt-in returns the task as EMPTY SUCCESS; otherwise classifier gets FIRST shot (access/balance must win even when the failed task carries billing metadata); remaining failures become `DataforseoChargedTaskError` when cost is present else INTERNAL_ERROR. `describeInvalidField` appends `(sent field=value)` to opaque "Invalid Field: 'x'" rejections by echoing the posted `task.data`. Task_post success uses `okTaskStatusCode=20100`.
**Invariant:** Match "no search results" on the STATUS MESSAGE, not code 40501 alone — 40501 also covers validation rejections that are real charged failures. Classification order is load-bearing: access/balance errors must be classified before any charge is recorded. The zod `billingMetadataSchema` safeParse is the only guard guaranteeing a call can be billed.
**Probe:** `src/server/lib/dataforseo/endpoints.test.ts` (ladder branches incl. no-results-as-empty and invalid-field echo).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-seo", query: "assertOk treatNoResultsAsEmpty DataforseoChargedTaskError isTaskInProgress", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-way branch (access-classified / charged-failed / empty-success / hard error) as a single shared ladder for any multi-endpoint paid API. Adapt code constants and message matchers to your vendor. Omit the SDK-mismatch hand-schema rationale.
