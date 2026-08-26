<!-- capsule-v2 -->
# Ensemble retry — run parallel LLM members, retry once on empty output, preserve accumulated usage

**Source:** Veda (`veda-ts`, MIT, `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`); Codebase Memory `veda`. **Question:** How does a multi-model ensemble run several LLM members in parallel, retry a member whose response is empty (a transient "conk out") without retrying hard failures, and report per-member usage and a successful-text list?

## Parallel ensemble with retry-on-empty
**Path/Symbol:** `src/core/ensemble.ts:runEnsemble` (34–102).
**Signature:** `runEnsemble(members: EnsembleMember[], onEvent?) → Promise<EnsembleResult>`.
**Data Shape:** `EnsembleMember = { id, request: LlmRequest }`; `EnsembleOutput = { id, text, usage?, error?, backendErrors? }`; `EnsembleResult = { outputs, successful: string[], totalUsage }`. `MAX_ATTEMPTS = 2` (retry once).

### Decisive source
```ts
const MAX_ATTEMPTS = 2;
// per member:
let attempts = 0; let accumulatedUsage = { inputTokens: 0, outputTokens: 0 };
while (attempts < MAX_ATTEMPTS) {
  attempts++;
  try {
    const response = await runLlm({ ...member.request, onMessage: onEvent ? (m) => onEvent({memberId, message:m}) : undefined });
    if (response.usage) accumulatedUsage = combineUsage([accumulatedUsage, response.usage]); // charges even for empty output
    if (response.text || response.errors.length > 0) return { id, text: response.text, usage: accumulatedUsage, backendErrors: response.errors.length ? response.errors : undefined };
    // empty text + no errors → transient, loop continues (retry)
  } catch (error) {
    return { id, text: '', error: String(error), usage: accumulatedUsage.inputTokens > 0 ? accumulatedUsage : undefined }; // fail fast, no retry
  }
}
return { id, text: '', usage: accumulatedUsage }; // exhausted retries
// successful = outputs.filter(r => !r.error && !r.backendErrors?.length && r.text).map(r => r.text)
```

**Flow:** run all members in parallel via `Promise.all`; each member loops up to `MAX_ATTEMPTS`; a response with text or backend errors returns immediately; an empty response with no errors retries; an exception returns immediately with the error and any accumulated usage; usage accumulates across attempts because providers charge even for empty output. `successful` collects only members with text and no errors/backend-errors.

**Invariant:** a member is retried only on empty-text-with-no-errors (transient); hard failures (backend errors or exceptions) never retry; usage from every attempt is preserved even when the member ultimately fails or returns empty; `totalUsage` sums all members' accumulated usage.

**Probe:** `tests/core/ensemble-retry.test.ts` — success-on-first (1 call), empty-then-success (2 calls, usage accumulated 200/50), empty-on-both (returns empty, 200/0, filtered from `successful`), backend-error (no retry, `backendErrors` set), exception (no retry, `error` set), exception-after-accumulated-usage (preserves 100/0), multiple-members-retry-independently, and `totalUsage` summing. Coverage caveat: `tests/` is excluded from the index by design (`fast-pattern`), so this probe is source-grounded from the on-disk test file, not graph-covered.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "runEnsemble EnsembleMember MAX_ATTEMPTS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the parallel ensemble with retry-once-on-empty, fail-fast-on-error, and usage accumulation across attempts. Adapt the retry count, the empty-output threshold, and the per-member event wiring to the host. Omit the winner-rationale/judge selection that consumes the ensemble outputs unless a target needs it.
