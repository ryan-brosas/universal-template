<!-- capsule-v2 -->
# Remote poll loop — how do you decide a remote session is REALLY done when its status flips to idle between every tool turn?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What completion signals exist, how are transient idles debounced, and how does the loop avoid racing an external kill?

## Stable-idle debounce + per-type completion checkers + race bail
**Path/Symbol:** `src/tasks/RemoteAgentTask/RemoteAgentTask.tsx:538-799`: `startRemoteSessionPolling`; :60-86 `REMOTE_TASK_TYPES`/`registerCompletionChecker`.
**Signature:** `startRemoteSessionPolling(taskId: string, context: TaskContext): () => void`. Constants: `POLL_INTERVAL_MS=1000`, `REMOTE_REVIEW_TIMEOUT_MS=30*60*1000`, `STABLE_IDLE_POLLS=5`.
**Data Shape:** `RemoteTaskCompletionChecker = (remoteTaskMetadata | undefined) => Promise<string | null>` — non-null string completes the task (string becomes notification text); registry keyed by remoteTaskType; "Checkers that hit external APIs should self-throttle". Checkers survive --resume because sidecar carries remoteTaskType.

### Decisive source
```ts
// Remote sessions flip to 'idle' between tool turns. With 100+ rapid
// turns, a 1s poll WILL catch a transient idle mid-run. Require stable
// idle (no log growth for N consecutive polls) before believing it.
const STABLE_IDLE_POLLS = 5;
...
let raceTerminated = false;
updateTaskState<RemoteAgentTaskState>(taskId, context.setAppState, prevTask => {
  if (prevTask.status !== 'running') {
    raceTerminated = true;   // stopTask raced while the poll was in-flight
    return prevTask;
  }
  ...
});
if (raceTerminated) return;
```

**Flow:** 1s poll → delta events appended to accumulatedLog + output file → archived ⇒ complete; registered checker non-null ⇒ complete with its string; result-message lookup skipped for isUltraplan/isLongRunning ("result(success) fires after every CCR turn") → review tasks: delta-scan for the `<remote-review>` tag, parse `<remote-review-progress>` heartbeats via lastIndexOf (extractTag returns FIRST match which "would always be the earliest value (0/0)"), bughunter-vs-prompt mode discriminated by SessionStart-hook presence, timeout checked EVEN IN THE CATCH so persistent API errors can't poll forever (error path also resets consecutiveIdlePolls) → every terminal exit runs evict + removeRemoteAgentMetadata + stops polling.
**Invariant:** Idle means nothing until stable ×5 AND hasAnyOutput. The post-await race guard must re-check status inside the updater and abandon side effects if killed externally — otherwise a killed task gets re-completed by the in-flight poll. Kill leaves the REMOTE session alive deliberately ("the claude.ai URL stays valid... TTL reaps it"); only local state dies.
**Probe:** `grep -n 'STABLE_IDLE_POLLS = 5' src/tasks/RemoteAgentTask/RemoteAgentTask.tsx` (:545) and `grep -c 'raceTerminated' src/tasks/RemoteAgentTask/RemoteAgentTask.tsx` (4) and `grep -n 'poll forever' src/tasks/RemoteAgentTask/RemoteAgentTask.tsx` (:766).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "startRemoteSessionPolling", limit: 5 });
```

## Verdict
Adopt stable-idle debounce, checker registry, and the catch-path timeout verbatim. Adapt event shapes to your remote protocol. Omit review-progress heartbeat parsing unless you carry ultrareview.
