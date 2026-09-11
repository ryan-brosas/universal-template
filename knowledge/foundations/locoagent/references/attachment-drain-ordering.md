<!-- capsule-v2 -->
# Attachment drain ordering — why must queued commands, attachments, and prefetch drains happen AFTER tool results but BEFORE the next model call?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Where in the turn do injected context messages legally sit, and what breaks if they are interleaved wrongly?

## Post-tool attachment block
**Path/Symbol:** `src/query.ts:1535-1643`: queue snapshot (:1547-1578), `getAttachmentMessages` drain (:1580-1590), memory-prefetch consume gate (:1592-1614), skill-prefetch collect (:1616-1628), conditional dequeue (:1630-1643).
**Signature:** `getAttachmentMessages(null, updatedToolUseContext, null, queuedCommandsSnapshot, [...messagesForQuery, ...assistantMessages, ...toolResults], querySource)` — note input is null on inter-round drains (pass-11 orchestrator capsule covers the turn-start call).
**Data Shape:** everything yielded here is appended to `toolResults` so the next State's message array keeps tool_results → attachments order.

### Decisive source
```ts
// Be careful to do this after tool calls are done, because the API
// will error if we interleave tool_result messages with regular user messages.
// ...
// Remove only commands that were actually consumed as attachments.
const consumedCommands = queuedCommandsSnapshot.filter(
  cmd => cmd.mode === 'prompt' || cmd.mode === 'task-notification')
if (consumedCommands.length > 0) {
  for (const cmd of consumedCommands) {
    if (cmd.uuid) { consumedCommandUuids.push(cmd.uuid); notifyCommandLifecycle(cmd.uuid, 'started') }
  }
  removeFromQueue(consumedCommands)
}
```

**Flow:** after tools complete and abort checks pass: snapshot the queue ONCE (`sleepRan ? 'later' : 'next'` priority; slash commands EXCLUDED mid-turn — "they must go through processSlashCommand after the turn ends"; main thread drains `agentId===undefined`, subagents only `task-notification` addressed to them) → yield attachment messages + push to toolResults → consume memory prefetch ONLY if settled AND not already consumed (`consumedOnIteration` sentinel guards double-delivery across iterations) → collect skill prefetch → THEN remove exactly the snapshot's prompt/task-notification commands from the global queue, recording their uuids for the wrapper's completed-lifecycle notification on normal return.
**Invariant:** (1) never interleave attachments between a tool_use and its tool_result — the API rejects it, hence placement strictly after tool execution; (2) dequeue ONLY what was actually converted into an attachment this round (snapshot-then-filter) — unconditional removal destroys unseen commands (queued-command-drain capsule); (3) lifecycle notifications pair started-here/completed-in-wrapper through the shared uuid array — the asymmetric signal documented on query() (:229-238); (4) prefetch consumption is once-per-turn even though collection happens per iteration.
**Probe:** coverage caveat (no upstream tests). Deterministic probes: `sed -n '1535,1537p' src/query.ts` verbatim interleave warning; `grep -n "consumedCommandUuids" src/query.ts` → exactly 4 sites forming the handoff; `grep -n "consumedOnIteration" src/query.ts src/utils/attachments.ts`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "queuedCommandsSnapshot getAttachmentMessages drain", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt post-tools placement + snapshot-scoped dequeue; adapt collector set; omit teammate scoping if single-agent. Porting trap: draining attachments before tool results finish yields API-invalid interleavings; dequeuing before conversion drops user prompts silently.
