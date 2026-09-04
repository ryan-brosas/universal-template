<!-- capsule-v2 -->
# Foreground/background agent duality — how does a foreground subagent become backgrounded without restarting its query loop?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What is the signal mechanism that interrupts the agent loop at the next tool-round boundary, and how do auto-background timers avoid double-flipping?

## Promise resolver map as cross-layer interrupt; timer + user race guarded by isBackgrounded
**Path/Symbol:** `src/tasks/LocalAgentTask/LocalAgentTask.tsx:517-652`: `backgroundSignalResolvers` module map, `registerAgentForeground`, `backgroundAgentTask`; :466-515: `registerAsyncAgent`.
**Signature:** `registerAgentForeground(...): { taskId, backgroundSignal: Promise<void>, cancelAutoBackground? }`; `backgroundAgentTask(taskId, getAppState, setAppState): boolean`.
**Data Shape:** module-level `Map<string, () => void>` keyed by taskId; the runner awaits `backgroundSignal` between turns; `isBackgrounded:false` marks foreground registration.

### Decisive source
```ts
// Map of taskId -> resolve function for background signals
const backgroundSignalResolvers = new Map<string, () => void>();
...
const timer = setTimeout((setAppState, agentId) => {
  setAppState(prev => {
    const prevTask = prev.tasks[agentId];
    if (!isLocalAgentTask(prevTask) || prevTask.isBackgrounded) {
      return prev;              // user already backgrounded it — no-op
    }
    return { ...prev, tasks: { ...prev.tasks,
      [agentId]: { ...prevTask, isBackgrounded: true } } };
  });
  const resolver = backgroundSignalResolvers.get(agentId);
  if (resolver) { resolver(); backgroundSignalResolvers.delete(agentId); }
}, autoBackgroundMs, setAppState, agentId);
```

**Flow:** foreground spawn registers task with `isBackgrounded:false` and stores a promise resolver → either user action (`backgroundAgentTask`) or the auto-background timeout flips state AND resolves → the awaited promise releases inside runAgent's loop at the next boundary → query continues detached. Resolver is deleted on use AND on `unregisterAgentForeground`. `cancelAutoBackground()` clears the timer when the command finishes first.
**Invariant:** State flip and signal resolution are two steps — the guard `!prevTask.isBackgrounded` inside BOTH paths makes whichever fires second a no-op, so user-click vs timer race cannot double-resolve or re-flip. The map must be module-level (survives across React renders); per-component storage would orphan resolvers.
**Probe:** `grep -n 'Map of taskId -> resolve function' src/tasks/LocalAgentTask/LocalAgentTask.tsx` (:517) and `grep -n 'Not yet backgrounded - running in foreground' src/tasks/LocalAgentTask/LocalAgentTask.tsx` (:566) and `grep -c 'backgroundSignalResolvers.delete' src/tasks/LocalAgentTask/LocalAgentTask.tsx` (3).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "registerAgentForeground", limit: 5 });
```

## Verdict
Adopt the resolver-map interrupt pattern verbatim — it is the minimal bridge between UI events and an async loop. Adapt where your loop checks the signal. Omit cancelAutoBackground if you have no auto-background timer.
