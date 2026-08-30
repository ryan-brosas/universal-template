<!-- capsule-v2 -->
# Live-progress JSONL tap — how does a parent watch subagent tool calls in real time from stdout?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** How are child agent events parsed, aggregated, and throttled into UI state?

## Line-buffered parse → progress reducer → 100ms notify throttle
**Path/Symbol:** `swarm/progress.ts:updateProgress` (:58-93) + `extractArgsPreview` (:95-105); `swarm/live-progress.ts:updateLiveWorker` (:51-65) + `throttledNotify` (:67-91); consumer `swarm/spawn.ts:attachHandlers.stdout` (:345-365).
**Signature:** `updateProgress(progress: AgentProgress, event: PiEvent, startTime: number): void`; key = `${cwd}::${taskId||spawn-<id>}`.
**Data Shape:** pi JSON events consumed: `tool_execution_start`, `tool_execution_end`, `message_end` (usage.input+output accumulate tokens; errorMessage latches). Preview picks FIRST present of `['command','path','file_path','pattern','query']`, newline-stripped, 60-char ellipsized.

### Decisive source
```ts
state.buffer += data.toString();
const lines = state.buffer.split('\n');
state.buffer = lines.pop() ?? '';        // keep partial line for next chunk
for (const line of lines) {
  const event = parseJsonlLine(line);
  if (!event) continue;
  updateProgress(state.progress, event, state.startMs);
  updateLiveWorker(...);
}
```
```ts
// deep-equality gate BEFORE set+notify
if (!workerInfoChanged(existing, info)) return;
liveWorkers.set(key, { ...info, cwd });
throttledNotify();   // min 100ms between listener flushes, trailing edge scheduled
```

**Flow:** stdout chunks accumulate in a buffer that always retains the trailing partial line (JSONL framing across chunks); each complete line parses → mutates one AgentProgress object → pushes a COPY of recentTools into the live-worker registry only if deep-equal check fails → listeners fire immediately or via one trailing timer ≤100ms later.
**Invariant:** The pop-retain split is the classic JSONL framing invariant — porters who split without retaining the tail drop events under load. The equality gate prevents render flicker from token-count noise; recentTools entries are copied per update because the shared progress object keeps mutating.
**Probe:** direct tests `tests/swarm/render-agents-row.test.ts::shows multiple live workers with different names on the same task` (:76) + `::deduplicates by worker name, not by task ID` (:105), `tests/feed-scroll.test.ts` scroll math; `grep -c "lines.pop() ?? ''" swarm/spawn.ts` (=1); `grep -c "MIN_NOTIFY_INTERVAL_MS = 100" swarm/live-progress.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "updateProgress updateLiveWorker throttledNotify extractArgsPreview", limit: 6 });
```

## Verdict
Adopt buffer-retaining JSONL tap + reducer + change-gated throttled notify for observing child agent processes; adapt the event-type vocabulary to your runner's protocol; omit preview heuristics freely.
