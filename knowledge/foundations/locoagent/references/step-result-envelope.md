<!-- capsule-v2 -->
# Step-result envelope — how does a multi-step executor report partial completion so the engine can classify the run?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What is the shared stdout contract that lets the workflow engine tell "succeeded", "partially failed", and "nothing to do" apart?

## Load the matching source dump
**Path/Symbol:** `workflows/executors/x-search-reply.ts`: `StepResult` + ledger (`:171-182`), `outputResult` (`:188-206`). Same convention: `hf-daily-papers.ts` `outputResult` (`:119-128`), `linkedin-search-reply.ts`, `hf-papers-to-x.ts`.
**Signature:** `StepResult { step: string; status: 'success' | 'failed' | 'skipped'; detail?: string }`; `outputResult()` prints ONE `console.log(JSON.stringify(result))` to STDOUT; `TOTAL_STEPS` is a module constant.
**Data Shape:** result `{ stepsCompleted, stepsTotal, ...domain, steps: StepResult[] }`; `stepsCompleted = steps.filter(s => s.status === 'success').length`.

### Decisive source
```ts
const steps: StepResult[] = []
const TOTAL_STEPS = 4
function outputResult() {
  const completedSteps = steps.filter(s => s.status === 'success').length
  const result = { stepsCompleted: completedSteps, stepsTotal: TOTAL_STEPS,
    searchQuery: config.searchQuery,
    posts: posts.map(p => ({ url: p.url, replied: p.replied, skippedDedup: p.skippedDedup, replyText: p.replyText?.slice(0,100) })),
    replied: repliedCount, skipped: skippedCount, failed: failedCount, steps }
  console.log(JSON.stringify(result))   // the ONE machine line
}
```

**Flow:** each step pushes its `StepResult` with a status as it completes → `outputResult` computes `stepsCompleted` from successes against the fixed `TOTAL_STEPS` → it emits a single JSON object to STDOUT (all narration went to STDERR during the run) → the engine classifies the run from `stepsCompleted`/`stepsTotal` and the per-step statuses.
**Invariant:** `stepsCompleted/stepsTotal` is the machine-readable completion ratio the engine keys on; a step that legitimately has no work records `skipped` (NOT `failed`), so a fully-done day reports full success with skipped rows — `skipped` is a normal state, `failed` is the only error signal. The ratio is computed from the ledger, never from a hand-maintained counter, so it cannot drift from what actually ran. Domain fields (posts, counts) are trimmed for the machine line (`replyText.slice(0,100)`).
**Probe:** No direct test for these executors (coverage caveat — source-grounded). Deterministic probes: grep pins `TOTAL_STEPS = 4` at `x-search-reply.ts:178` and `console.log(JSON.stringify(result))` at `:205`; `search_graph --name-pattern "outputResult"` resolves it in all four executors (x-search-reply, hf-daily-papers, hf-papers-to-x, linkedin-search-reply) — a repo-wide convention, not a one-off.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "outputResult stepsCompleted stepsTotal StepResult", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt a fixed `TOTAL_STEPS` constant, a statused step ledger, `skipped`-not-`failed` for no-work, a computed completion ratio, and a single trimmed JSON stdout line for ANY multi-step executor the engine must classify. Adapt the domain fields. Omit nothing — treating `skipped` as `failed` misclassifies normal steady-state runs.
