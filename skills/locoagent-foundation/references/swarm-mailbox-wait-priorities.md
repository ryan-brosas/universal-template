<!-- capsule-v2 -->
# Mailbox wait priorities — in what order does an idle teammate consume shutdown, leader, peer, and task-list work?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** when a teammate's mailbox holds a flood of peer chatter plus one shutdown request, which message wins and why?

## waitForNextPromptOrShutdown anti-starvation ladder
**Path/Symbol:** `src/utils/swarm/inProcessRunner.ts:waitForNextPromptOrShutdown` (:689-868), `findAvailableTask` (:595-605), `tryClaimNextTask` (:624-657).
**Signature:** `(identity, abortController, taskId, getAppState, setAppState, taskListId) => Promise<WaitResult>` where WaitResult = `shutdown_request | new_message | aborted`.
**Data Shape:** 500ms poll; sources checked per iteration: AppState `task.pendingUserMessages[0]` (transcript-view injections) → mailbox file → team task list.

### Decisive source
```ts
// Scan all unread messages for shutdown requests (highest priority).
// readMailbox() already reads all messages from disk, so this scan
// adds only ~1-2ms of JSON parsing overhead.
// ...
// No shutdown request found. Prioritize team-lead messages over peer
// messages — the leader represents user intent and coordination, so
// their messages should not be starved behind peer-to-peer chatter.
// Fall back to FIFO for peer messages.
```
Task availability predicate (:600-604): pending ∧ unowned ∧ `task.blockedBy.every(id => !unresolvedTaskIds.has(id))`.

**Flow:** every loop: drain pendingUserMessages first (shift + return as from:'user') → sleep(500) except first iteration → re-check abort → readMailbox once, scan ALL unread for shutdown requests (mark-read by index, return with count of skipped unread for telemetry) → else first unread from `TEAM_LEAD_NAME` → else first unread ANY sender (FIFO) → else try claim next available task (claim + set in_progress + format "Complete all open tasks. Start with task #N") → repeat until abort.
**Invariant:** shutdown NEVER starves regardless of queue depth; leader intent outranks peer chatter; FIFO only within peers; errors during one mailbox read must not kill the poll loop; claiming is atomic-enough via claimTask failure logging (`Failed to claim task #N` — lost race just means no prompt this round).
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n 'prioritized over' src/utils/swarm/inProcessRunner.ts` (:792); `grep -n 'should not be starved' src/utils/swarm/inProcessRunner.ts` (:807-808).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "waitForNextPromptOrShutdown tryClaimNextTask findAvailableTask", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt explicit priority ladders in any idle-poll loop that multiplexes control messages, coordination traffic, and self-serve work queues; adapt intervals; omit the task-list arm if your system has no shared task store.
