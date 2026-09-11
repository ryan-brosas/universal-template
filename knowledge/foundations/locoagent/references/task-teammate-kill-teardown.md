<!-- capsule-v2 -->
# In-process teammate kill & UI cap — how is a teammate torn down across THREE shared structures, and why does the transcript mirror hold only 50 messages?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What must a teammate kill update besides the task itself, and what memory discipline governs the AppState message mirror?

## Task + teamContext.teammates + team file; capped append helper
**Path/Symbol:** `src/utils/swarm/spawnInProcess.ts:227-328`: `killInProcessTeammate`; `src/tasks/InProcessTeammateTask/types.ts` (whole): state shape, `TEAMMATE_MESSAGES_UI_CAP=50`, `appendCappedMessage`; `InProcessTeammateTask.tsx`: thin Task impl + inject/append helpers + `findTeammateTaskByAgentId` running-first lookup.
**Signature:** `killInProcessTeammate(taskId: string, setAppState: SetAppStateFn): boolean`; `appendCappedMessage<T>(prev: readonly T[] | undefined, item: T): T[]`.
**Data Shape:** two runtime-only AbortControllers with different scopes: `abortController` "kills WHOLE teammate", `currentWorkAbortController` "aborts current turn without killing teammate". Identity stored as PLAIN DATA ("TeammateContext is for AsyncLocalStorage; this is for AppState persistence").

### Decisive source
```ts
// Remove from teamContext.teammates using the agentId
let updatedTeamContext = prev.teamContext
if (prev.teamContext && prev.teamContext.teammates && agentId) {
  const { [agentId]: _, ...remainingTeammates } = prev.teamContext.teammates
  updatedTeamContext = { ...prev.teamContext, teammates: remainingTeammates }
}
...
onIdleCallbacks: [], // Clear callbacks to prevent stale references
messages: teammateTask.messages?.length
  ? [teammateTask.messages[teammateTask.messages.length - 1]!]
  : undefined,
pendingUserMessages: [],
```

**Flow:** kill aborts controller → unregisters cleanup → resolves pending onIdleCallbacks (unblocking waiters like engine.waitForIdle) → removes from teamContext.teammates INSIDE the same updater → AFTER the updater, removes member from the on-disk team file (`removeMemberByAgentId` — "outside state updater to avoid file I/O in callback") → evicts output, pre-notified so no XML, SDK bookend closed directly. The BQ-documented cap rationale: ~20MB RSS per agent at 500+ turns, whale session hit 36.8GB because task.messages mirrored every message; the full conversation lives in the runner's local array and on disk.
**Invariant:** A teammate exists in three places (AppState.tasks, teamContext.teammates, team file on disk) — missing any one leaks a ghost that can receive messages or block idle detection. Message injection into terminal teammates is rejected via `isTerminalTaskStatus`, but idle teammates still accept queued messages. `findTeammateTaskByAgentId` prefers RUNNING entries because killed tasks with the same agentId may linger.
**Probe:** `grep -n 'kills WHOLE teammate' src/tasks/InProcessTeammateTask/types.ts` (:36) and `grep -n 'reached 36.8GB' src/tasks/InProcessTeammateTask/types.ts` (:98) and `grep -n 'outside state updater' src/utils/swarm/spawnInProcess.ts` (:301).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "killInProcessTeammate", limit: 5 });
```

## Verdict
Adopt the three-place teardown checklist and the UI-mirror cap verbatim. Adapt identity/team storage to your swarm model. Omit plan-approval fields unless you carry plan mode per teammate.
