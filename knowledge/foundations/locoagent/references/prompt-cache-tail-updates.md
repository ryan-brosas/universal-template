<!-- capsule-v2 -->
# Prompt-cache-safe context updates — how does dynamic state reach the model without busting the cached prefix?

**Source:** locoagent (Claude Code CLI fork, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** where volatile facts may be injected so they never invalidate the prompt cache.

## date_change + tail-append rule
**Path/Symbol:** `src/utils/attachments.ts:getDateChangeAttachments` (:1402-1444), `getAgentListingDeltaAttachment` (:1477-1556), `getDeferredToolsDeltaAttachment` (:1454-1475), `getMcpInstructionsDeltaAttachment` (:1558-1585).
**Signature:** date: `(messages?) → Attachment[]` keyed off module-state `getLastEmittedDate/setLastEmittedDate`; deltas: pure functions over (tools/model/messages) diffing current pool vs announced-set reconstructed FROM THE TRANSCRIPT.
**Data Shape:** date_change carries `{ newDate }`; deltas carry added/removed name+line arrays with deterministic sort.

### Decisive source
```ts
// The date_change attachment is appended at the tail of the conversation,
// so the model learns the new date without mutating the cached prefix.
// messages[0] (from getUserContext → prependUserContext) intentionally
// keeps the stale date — clearing that cache would regenerate the prefix
// and turn the entire conversation into cache_creation on the next turn
// (~920K effective tokens per midnight crossing per overnight session).
// Exported for testing — regression guard for the cache-clear removal.
```

**Flow:** midnight crossing → compare `getLocalISODate()` vs last-emitted module state → emit ONE tail attachment with the new date (first turn records silently). Agent-listing delta exists because embedding the agent list in AgentTool's description caused "~10.2% of fleet cache_creation" whenever MCP connected/plugins reloaded; moving it to transcript-reconstructed diffs keeps tool schemas static. All three delta getters are exported for compact.ts (:567-578) which re-announces full sets with empty message history after compaction eats prior deltas. Deltas reconstruct the announced set by replaying prior `*_delta` attachments from messages — added names accumulate, removed delete — then diff against the live filtered pool, sorted with `localeCompare` because "agent load order is nondeterministic".
**Invariant:** never mutate anything before the last assistant message; new dynamic facts go in NEW TAIL MESSAGES, never by editing cached earlier ones; listings derived from nondeterministic sources must be sorted before emission or byte-comparison across turns fails; gates mirrored at compact call sites must stay single-source-of-truth (the getters themselves).
**Probe:** no upstream test (coverage caveat); the comment pins the regression rationale verbatim :1402-1414. Deterministic probe: `sed -n '567,585p' src/services/compact/compact.ts` shows all three re-announce calls.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "date_change agent_listing_delta deferred_tools_delta mcp_instructions_delta cache", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt tail-only mutation + transcript-reconstructed delta sets + deterministic sorting; adapt which pools get delta treatment; omit subscription-gated notes. Porting trap: "fixing" the stale date in messages[0] converts an overnight session into ~920K tokens of cache_creation at every midnight; another trap is unsorted listings that flip byte-identity across identical states.
