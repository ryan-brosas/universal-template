<!-- capsule-v2 -->
# Backgrounded main session — how does Ctrl+B background the MAIN query without corrupting the session transcript after /clear?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** Where does a backgrounded main-session query persist its transcript, and how do completion notifications differ for foregrounded vs backgrounded tasks?

## Isolated per-task transcript + reused AbortController + dual-path completion
**Path/Symbol:** `src/tasks/LocalMainSessionTask.ts` (whole :1-479): `registerMainSessionTask`, `completeMainSessionTask`, `enqueueMainSessionNotification`, `foregroundMainSessionTask`, `isMainSessionTask`, `startBackgroundSession`.
**Signature:** `registerMainSessionTask(description, setAppState, mainThreadAgentDefinition?, existingAbortController?): { taskId: string; abortSignal: AbortSignal }`.
**Data Shape:** reuses LocalAgentTaskState with `agentType:'main-session'` (the ONE predicate `isMainSessionTask` checks; pill/panel filters all agree on it via isPanelAgentTask). ID prefix `'s'`. DEFAULT_MAIN_SESSION_AGENT supplies an empty getSystemPrompt when no --agent definition exists.

### Decisive source
```ts
// Link output to an isolated per-task transcript file (same layout as
// sub-agents). Do NOT use getTranscriptPath() — that's the main session's
// file, and writing there from a background query after /clear would corrupt
// the post-clear conversation.
void initTaskOutputAsSymlink(taskId, getAgentTranscriptPath(asAgentId(taskId)))
...
const abortController = existingAbortController ?? createAbortController()
```

**Flow:** startBackgroundSession wraps `query()` in `runWithAgentContext` (AsyncLocalStorage scoping so skill invocations carry this task's agentId) → per-event incremental sidechain-transcript writes keyed by `lastRecordedUuid` keep TaskOutput live and survive mid-run symlink re-links → abort mid-stream path checks alreadyNotified before emitting 'stopped' → natural end calls completeMainSessionTask(success). Completion splits: still-backgrounded → XML notification via check-and-set latch; FOREGROUNDED → no XML ("TUI user is watching") but notified set anyway so eviction guards pass + emitTaskTerminatedSdk closes the bookend.
**Invariant:** Writing a background query's transcript to the main session's live file corrupts history across /clear — isolation by task-scoped path is non-negotiable. Foregrounding swaps `foregroundedTaskId` and restores the PREVIOUSLY foregrounded task back to background in the same update. The existingAbortController reuse is what makes "background the ACTIVE query" possible — creating a fresh controller would orphan the running loop from its kill switch.
**Probe:** `grep -n "would corrupt" src/tasks/LocalMainSessionTask.ts` (:104-105) and `grep -cn "recordSidechainTranscript" src/tasks/LocalMainSessionTask.ts` (4) and `grep -n "existingAbortController ?? createAbortController" src/tasks/LocalMainSessionTask.ts` (:114).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "registerMainSessionTask", limit: 5 });
```

## Verdict
Adopt transcript isolation + controller-reuse verbatim. Adapt notification split to your consumer model. Omit runWithAgentContext only if you have no ambient-context skill scoping to preserve.
