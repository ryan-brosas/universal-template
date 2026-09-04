<!-- capsule-v2 -->
# Bidirectional tasks (server as polling client) — when the SERVER's outbound elicitation/sampling request is executed by the CLIENT as a background task, how does the server-side tool wait for it?

**Source:** modelcontextprotocol/servers MIT `main@76d64c82`; Codebase Memory `servers`. **Question:** How must a server-side tool handle the fact that a client may answer a server-initiated request with EITHER a synchronous result OR a `CreateTaskResult`, and how does it poll to completion?

## Dual-schema response + tasks/get poll loop + tasks/result fetch
**Path/Symbol:** `src/everything/tools/trigger-sampling-request-async.ts` (whole file, 234L: dual capability gate :76–86; task-tagged request :89–113; z.union response :116–132; sync fallback :135–145; poll loop :147–197; result fetch :199–211). Structural twin: `src/everything/tools/trigger-elicitation-request-async.ts` (whole file, 269L — same ladder with `elicitation/create`, POLL_INTERVAL 1000ms and MAX_POLL_ATTEMPTS 600 :23–26 for user-paced input). Both registered inside `registerConditionalTools` (`tools/index.ts`).

**Signature:** gate = `clientCapabilities.tasks?.requests?.sampling?.createMessage !== undefined` (alongside the base `clientCapabilities.sampling !== undefined`) / twin gates `tasks.requests.elicitation.create`. Outbound request carries `params.task: { ttl }` — the marker that ASKS the client to execute as a task. Response parsed with `z.union([{ task: { taskId, status, pollInterval?, statusMessage? } }, <synchronous-result-shape>])`; polls use `z.looseObject({ status, statusMessage? })`.

**Data Shape:** `statusMessages: string[]` accumulates a progress transcript that is echoed into every failure/timeout/success content block; loop exits on `completed | failed | cancelled | attempts >= MAX_POLL_ATTEMPTS`.

### Decisive source
```ts
// trigger-sampling-request-async.ts:116-146 — accept BOTH execution modes from one sendRequest
const samplingResponse = await extra.sendRequest(request, z.union([
  // CreateTaskResult - client created a task
  z.object({ task: z.object({ taskId: z.string(), status: z.string(),
    pollInterval: z.number().optional(), statusMessage: z.string().optional() }) }),
  // CreateMessageResult - synchronous execution
  z.object({ role: z.string(), content: z.any(), model: z.string(),
    stopReason: z.string().optional() }),
]));
// Check if client returned CreateTaskResult (has task object)
const isTaskResult = "task" in samplingResponse && samplingResponse.task;
if (!isTaskResult) { /* return the direct response as [SYNC] */ }
...
while (taskStatus !== "completed" && taskStatus !== "failed" &&
       taskStatus !== "cancelled" && attempts < MAX_POLL_ATTEMPTS) {
  await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL));
  attempts++;
  const pollResult = await extra.sendRequest(
    { method: "tasks/get", params: { taskId } },
    z.looseObject({ status: z.string(), statusMessage: z.string().optional() }));
```

**Flow:** dual capability gate (base feature AND its async-tasks sub-capability; unmet ⇒ tool never registers) → send request with `params.task.ttl` → client answers synchronously (`[SYNC]` passthrough, done) or with `{ task }` → fixed-interval `tasks/get` polling (1s; 60 attempts ≈ 5min for sampling, 600 attempts ≈ 10min for human elicitation) → terminal branch: timeout `[TIMEOUT]`, failed/cancelled `[FAILED]/[CANCELLED]` with statusMessage, else `tasks/result { taskId }` fetch → format result WITH the full statusMessages transcript.

**Invariants:**
1. **Never assume the execution mode:** one request can be answered either way; discriminating on `"task" in response` is mandatory before touching `.taskId`. A porter who assumes task mode breaks every legacy client (and vice versa).
2. **Poll loops need a bounded attempt cap** independent of TTL — the network may deliver statuses forever.
3. **Preserve the audit trail:** append every status change to `statusMessages` and include it in ALL outcome branches — debugging an async flow without the poll history is blind.
4. **The async sub-capability is distinct from the feature:** declaring `sampling: {}` does NOT mean the client accepts task-executed sampling; only `tasks.requests.sampling.createMessage` authorizes it.

**Probe:** `src/everything/__tests__/tools.test.ts:535–603` pins the SYNC twin's registration gating (`should not register when client does not support sampling`) and round-trip; the async twins are exercised at the handler level via mock `sendRequest` sequences (see tools.test.ts registration-gate cases :721–832 for the URL-elicitation sibling pattern; coverage caveat: no dedicated integration test drives the async poll loop end-to-end — deterministic probe is the mock-handler contract above).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "tasks/get tasks/result poll interval bidirectional sampling elicitation async", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the dual-mode response union, the two-key capability gate, bounded polling with transcript accumulation, and per-feature poll budgets (machine work ≪ human input); adapt intervals/caps to your latency profile; omit the demo formatting. Complements `task-based-tool-authoring.md` (server AS task provider): together they cover both sides of the bidirectional task exchange.
