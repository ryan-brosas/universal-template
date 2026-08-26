<!-- capsule-v2 -->
# Teammate loop cache discipline — how does an agent loop that reruns runAgent() across prompts keep the prompt cache alive?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** what per-teammate state must persist across loop iterations so each turn's API prefix matches the previous turn's?

## Persistent contentReplacementState + isolated compaction
**Path/Symbol:** `src/utils/swarm/inProcessRunner.ts:runInProcessTeammate` (:883-1534); replacement-state creation :1035-1045, reset-on-compact :1108-1113; isolated context :1081-1089; mirror compaction :1118-1125.
**Signature:** `(config: InProcessRunnerConfig) => Promise<InProcessRunnerResult>`.
**Data Shape:** `allMessages: Message[]` accumulates FULL original tool results across prompts; `teammateReplacementState` created ONCE before the while-loop.

### Decisive source
```ts
// Per-teammate content replacement state. The while-loop below calls
// runAgent repeatedly over an accumulating `allMessages` buffer (which
// carries FULL original tool result content, not previews — query() yields
// originals, enforcement is non-mutating). Without persisting state across
// iterations, each call gets a fresh empty state from createSubagentContext
// and makes holistic replace-globally-largest decisions, diverging from
// earlier iterations' incremental frozen-first decisions → wire prefix
// differs → cache miss. Gated on parent to inherit feature-flag-off.
```
Compaction isolation (:1081-1087): `{ ...toolUseContext, readFileState: cloneFileStateCache(...), onCompactProgress: undefined, setStreamMode: undefined }` — "so that compaction does not clear the main session's readFileState cache or trigger the main session's UI callbacks."

**Flow:** per iteration: token estimate vs autoCompactThreshold → compact if needed (isolated context; `resetMicrocompactState()` because full compact replaces all messages/old tool IDs; recreate replacement state — "Stale Map entries are harmless (UUID keys never match) but accumulate memory over long runs"; mirror compacted messages into task.messages so the AppState mirror doesn't grow unbounded 10-50MB; mutate allMessages IN PLACE via `.length = 0`) → runAgent with forkContextMessages + per-turn `currentWorkAbortController` (Escape stops THIS turn only, lifecycle abort kills teammate — checked in this order after every yielded message).
**Invariant:** replacement decisions must be incremental-frozen-first across turns (fresh state each call ⇒ divergent wire prefix ⇒ cache miss); compaction of a teammate must never touch leader caches/UI callbacks; dual-abort semantics: lifecycle > work.
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n 'wire prefix' src/utils/swarm/inProcessRunner.ts` (:1041-1042); `grep -n 'cloneFileStateCache' src/utils/swarm/inProcessRunner.ts` (:1086).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "runInProcessTeammate createContentReplacementState compactConversation buildPostCompactMessages", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt persistent-per-agent replacement/reduction state for any multi-turn agent loop reusing one message buffer, plus cloned caches for nested compaction; adapt thresholds; omit the feature-flag gating if you have no flag infra.
