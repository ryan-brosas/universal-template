<!-- capsule-v2 -->
# Queued-command drain contract — how do user prompts and system notifications become mid-turn attachments without being lost?

**Source:** locoagent (Claude Code CLI fork, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** the drain-side half of the queue that survives even bare mode.

## getQueuedCommandAttachments / getAgentPendingMessageAttachments
**Path/Symbol:** `src/utils/attachments.ts:getQueuedCommandAttachments` (:1046-1083), `INLINE_NOTIFICATION_MODES` (:1044), `getAgentPendingMessageAttachments` (:1085-1101); bare-mode escape :752-761; subagent drain gate `src/query.ts:1575-1580`.
**Signature:** `(queuedCommands: QueuedCommand[]) → Promise<Attachment[]>`; pending variant `(toolUseContext) → Attachment[]`.
**Data Shape:** filter keeps modes in `Set(['prompt', 'task-notification'])`; output carries provenance — `source_uuid`, `commandMode`, `origin`, `isMeta`.

### Decisive source
```ts
// Include both 'prompt' and 'task-notification' commands as attachments.
// During proactive agentic loops, task-notification commands would otherwise
// stay in the queue permanently (useQueueProcessor can't run while a query
// is active), causing hasPendingNotifications() to return true and Sleep to
// wake immediately with 0ms duration in an infinite loop.
const filtered = queuedCommands.filter(_ => INLINE_NOTIFICATION_MODES.has(_.mode))
// bare-mode comment :756-760:
// query.ts:removeFromQueue dequeues these unconditionally after
// getAttachmentMessages runs — returning [] here silently drops them.
// Coworker runs with --bare and depends on task-notification...
```

**Flow:** orchestrator passes an ALREADY agent-scoped queue snapshot (main thread gets `agentId===undefined`, subagents only commands stamped with theirs — query.ts drain gate "Subagents only drain task-notifications addressed to them") → mode filter → per command: pasted images become resized base64 content blocks prepended to text → typed `queued_command` preserving origin/isMeta provenance. Subagent coordinator messages arrive via a SEPARATE channel: `drainPendingMessages(agentId, getAppState, setAppState)` mapped to `queued_command` with `origin:{kind:'coordinator'}, isMeta:true`.
**Invariant:** the queue is consumed elsewhere (removeFromQueue) unconditionally after collection — a collector that returns [] doesn't defer items, it DESTROYS them, hence the bare-mode escape hatch exists specifically to keep this collector alive when all others are disabled; draining task-notifications inline breaks the Sleep-wake infinite loop; mid-turn drains preserve origin/isMeta so downstream can distinguish human-typed from system-injected.
**Probe:** no upstream test (coverage caveat). Deterministic probe: comments pinned verbatim :1052-1056 and :756-760; drain gate at `src/query.ts:1575-1578`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "queued_command INLINE_NOTIFICATION_MODES drainPendingMessages removeFromQueue", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt provenance-preserving drain with mode filtering and unconditional-consumer awareness; adapt queue modes; omit image paste handling. Porting trap: skipping the collector under any "simple/disabled" flag silently eats every queued notification because removal happens regardless; forgetting the subagent agentId filter lets subagents swallow user prompts addressed to the main thread.
