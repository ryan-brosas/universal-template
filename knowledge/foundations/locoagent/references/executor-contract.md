<!-- capsule-v2 -->
# Executor protocol: stop-checkpoints, dedup store, and machine output — how does a step pipeline stay interruptible, idempotent, and reportable?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What must every workflow executor do so the engine can stop it mid-flight, re-run it without duplicate side effects, and classify its outcome?

## The three executor obligations (stop / dedup / JSON result line)
**Path/Symbol:** `workflows/executors/x-search-reply.ts`:`checkWorkflowStopped` (`:107-116`), replied-store (`:75-103`), `outputResult` (`:188-206`), reply loop with 3-attempt verify (`:429-479`).
**Signature:** `checkWorkflowStopped(): boolean`; `ab(cmd): string` (agent-browser via execSync, 30 s timeout, error-swallowing); final act `console.log(JSON.stringify(result))`.
**Data Shape:** Steps ledger `StepResult { step, status: 'success'|'failed'|'skipped', detail? }`; result `{ stepsCompleted, stepsTotal, ..., steps }` printed as the ONE stdout JSON line the engine parses; dedup store `{ version, description, posts: [{ postUrl, repliedAt, searchQuery }] }`.

### Decisive source
```ts
function checkWorkflowStopped(): boolean {
  try {
    if (!existsSync(STATE_PATH)) return false
    const state = JSON.parse(readFileSync(STATE_PATH, 'utf-8'))
    return state.workflows?.[id]?.status === 'stopped'
  } catch (_) {}   // any read problem ⇒ keep running; stop is advisory
  return false
}
// ...inside the per-post loop:
if (checkWorkflowStopped()) break          // cooperative stop at a checkpoint
// after each successful post — save dedup IMMEDIATELY, not at the end:
repliedStore.posts.push({ postUrl: post.url, repliedAt: new Date().toISOString(), searchQuery })
saveReplied(repliedStore)
```
and the post-verify retry:
```ts
for (let attempt = 1; attempt <= 3; attempt++) {
  ab(`click @${replyBtnMatch[1]}`); ab('wait 4000')
  const verify = ab("snapshot -i -c -s '[role=\"textbox\"]'")
  if (!verify.includes(post.replyText.slice(0, 20))) { posted = true; break }
}
```

**Flow:** load per-workflow dedup store → enumerate targets (URL regex `/\/status\/\d+$/`, exclude own username) → skip already-done entries → per item: stop-checkpoint → act → VERIFY by observing page state (textbox emptied), not by trusting the click's exit code → on success persist dedup immediately → on 3 failed attempts clear the textbox so the "Leave site?" dialog can't block later navigation → print one JSON result line to STDOUT (all narration goes to STDERR).
**Invariant:** Success is defined by post-action verification, and the dedup record is written the moment verification passes — a crash between action and save would lose exactly that entry, so nothing else may delay it. Stop checks are advisory reads of engine state; executors must tolerate state-file absence/corruption. Stdout belongs to the machine contract; human-readable logs go to stderr.
**Probe:** No direct test for this executor (coverage caveat — source-grounded). Deterministic probe: `search_graph --name-pattern "checkWorkflowStopped"` resolves it in all three executors (x-search-reply, linkedin-search-reply, hf-papers-to-x) — the pattern is repo-wide convention, not a one-off.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "executor checkWorkflowStopped outputResult stepsCompleted", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt cooperative stop-checkpoints, verify-by-observation with bounded retries, immediate dedup persistence, stderr-narration/stdout-JSON separation. Adapt selectors, waits, and the LLM call (here DeepSeek-compatible `/chat/completions` with a config-supplied system prompt). Omit the X-specific scraping logic — the obligations, not the domain, are the reusable contract.
