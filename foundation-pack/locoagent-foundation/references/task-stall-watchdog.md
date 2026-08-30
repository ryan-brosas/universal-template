<!-- capsule-v2 -->
# Shell-task stall watchdog — how does a background command that is silently waiting on an interactive prompt get surfaced without any stream listener?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How do you detect "the process is blocked on stdin" from the OUTPUT side only, and what notification shape does it emit?

## Output-size stagnation + last-line prompt heuristics + one-shot latch
**Path/Symbol:** `src/tasks/LocalShellTask/LocalShellTask.tsx:24-104`: `STALL_CHECK_INTERVAL_MS=5_000`, `STALL_THRESHOLD_MS=45_000`, `STALL_TAIL_BYTES=1024`, `PROMPT_PATTERNS`, `looksLikePrompt`, `startStallWatchdog`.
**Signature:** `startStallWatchdog(taskId: string, description: string, kind: BashTaskKind | undefined, toolUseId?, agentId?): () => void` — returns cancel.
**Data Shape:** monitors (`kind === 'monitor'`) get a no-op watchdog. Prompt patterns match the LAST line only: `(y/n)`/`[Y/n]` case-insensitive, `(yes/no)`, directed-question regex `\b(?:Do you|Would you|Shall I|Are you sure|Ready to)\b.*\? *$`, `Press (any key|Enter)`, `Continue?`, `Overwrite?`.

### Decisive source
```ts
const timer = setInterval(() => {
  void stat(outputPath).then(s => {
    if (s.size > lastSize) { lastSize = s.size; lastGrowth = Date.now(); return }
    if (Date.now() - lastGrowth < STALL_THRESHOLD_MS) return
    void tailFile(outputPath, STALL_TAIL_BYTES).then(({ content }) => {
      if (cancelled) return
      if (!looksLikePrompt(content)) {
        // Not a prompt — keep watching. Reset so the next check is
        // 45s out instead of re-reading the tail on every tick.
        lastGrowth = Date.now()
        return
      }
      cancelled = true            // Latch before visible side effects
      clearInterval(timer)
```

**Flow:** every 5s stat the output file → grew? reset clock → stalled ≥45s AND tail looks like an interactive prompt → enqueue a priority-'next' task_notification carrying the tail + remediation advice ("re-run with piped input e.g. `echo y | command`") → latch cancelled BEFORE clearing so an overlapping in-flight tick bails.
**Invariant:** The stall notification carries NO `<status>` tag — print.ts treats `<status>` as terminal and an unknown value falls through to 'completed', which would falsely CLOSE the task for SDK consumers; statusless notifications are skipped by the SDK emitter (progress ping only). A non-prompt stall resets lastGrowth rather than re-tailing every tick. The watchdog never kills anything — it only notifies.
**Probe:** `grep -n "STALL_THRESHOLD_MS = 45" src/tasks/LocalShellTask/LocalShellTask.tsx` (:26) and `grep -n "No <status> tag" src/tasks/LocalShellTask/LocalShellTask.tsx` (:76-77) and `grep -c "if (kind === 'monitor') return () => {}" src/tasks/LocalShellTask/LocalShellTask.tsx` (1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "startStallWatchdog", limit: 5 });
```

## Verdict
Adopt the size-delta watchdog + last-line prompt heuristic verbatim (pure functions over file stats). Adapt pattern list to your ecosystem's common prompts. Omit nothing else — the monitor exemption is load-bearing.
