<!-- capsule-v2 -->
# Activity tracker debounce choreography — how are tool events turned into feed lines without flooding the channel?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** What debouncing/throttling separates noisy tool traffic from durable feed events and registry writes?

## Per-path edit debounce + trailing registry flush + 60s recent windows
**Path/Symbol:** `extension/activity.ts` — `EDIT_DEBOUNCE_MS = 5000` (:15), `REGISTRY_FLUSH_MS = 10000` (:16), `RECENT_WINDOW_MS = 60_000` (:17), `debouncedLogEdit` (:54-71), `scheduleRegistryFlush` (:73-79), `isGitCommit/isTestRun/extractCommitMessage` (:81-94).
**Signature:** `createActivityTracker({state, dirs, config}) → {handleToolCall, handleToolResult, scheduleRegistryFlush, dispose}`.
**Data Shape:** pendingEdits Map<path, timer>; single-slot registryFlushTimer on state; counters recentTestRuns/recentEdits reset by one timer each.

### Decisive source
```ts
function debouncedLogEdit(filePath: string): void {
  const existing = pendingEdits.get(filePath);
  if (existing) clearTimeout(existing);            // per-PATH: rapid edits to one file collapse
  pendingEdits.set(filePath, setTimeout(() => {
    logFeedEvent(process.cwd(), state.agentName, 'edit', filePath, ...);
    pendingEdits.delete(filePath);
  }, EDIT_DEBOUNCE_MS));
}
```
```ts
if (state.registryFlushTimer) return;             // single-flight: at most one flush per 10s
```
Commit/test classification:
```ts
const isGitCommit = (command: string): boolean => /\bgit\s+commit\b/.test(command);
const isTestRun = /\b(npm\s+test|npx\s+(jest|vitest|mocha)|pytest|go\s+test|cargo\s+test|bun\s+test)\b/.test(command);
const extractCommitMessage = (command: string): string => (command.match(/-m\s+["']([^"']+)["']/) ?? ['', ''])[1] ?? '';
```

**Flow:** tool_call updates activity + increments session.toolCalls + schedules the trailing registry flush (10s single-flight) and sets currentActivity strings (`editing X`, `reading X`, `committing`, `running tests`). tool_result emits commit/test/edit feed lines (edit only after its debounce fires), records filesModified as move-to-end capped ring of 20, clears currentActivity. dispose() drains ALL timers including per-path edits so shutdown never leaks a late write.
**Invariant:** The registry flush is TRAILING (fires only after 10s of quiet-ish usage via single-flight latch from first trigger) — porters who write-per-tool-call hammer the registry file and break the mtime sync bridge's cheapness. Commit message regex requires quoted `-m "..."` forms; unquoted messages yield empty previews by design.
**Probe:** direct tests `tests/swarm/session-shutdown-cleanup.test.ts::should log feed events when agent leaves and tasks are unclaimed` (:283 class); `grep -c "EDIT_DEBOUNCE_MS = 5000" extension/activity.ts` (=1); `grep -n "files.length > 20" extension/activity.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "debouncedLogEdit scheduleRegistryFlush isGitCommit isTestRun addModifiedFile", limit: 5 });
```

## Verdict
Adopt per-path edit debounce + single-flight trailing registry flush + windowed counters for activity feeds; adapt the test-runner regex set; omit auto-status text if you have no presence UI.
