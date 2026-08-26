<!-- capsule-v2 -->
# Master attachment orchestrator — how does one turn-boundary call gather ~25 context kinds without one failure killing the turn?

**Source:** locoagent (Claude Code CLI fork, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** the concurrency, isolation, and phase-ordering contract of the per-turn context sweep.

## getAttachments
**Path/Symbol:** `src/utils/attachments.ts:getAttachments` (:743-1003).
**Signature:** `(input: string | null, toolUseContext: ToolUseContext, ideSelection: IDESelection | null, queuedCommands: QueuedCommand[], messages?: Message[], querySource?: QuerySource, options?: { skipSkillDiscovery?: boolean }): Promise<Attachment[]>`.
**Data Shape:** input = current user prompt (null on inter-turn tool rounds); returns flat `Attachment[]`; every collector returns arrays (never singletons).

### Decisive source
```ts
const abortController = createAbortController()
const timeoutId = setTimeout(ac => ac.abort(), 1000, abortController)
// ...
maybe('at_mentioned_files', () => processAtMentionedFiles(input, context)), // phase 1: user-input
const userAttachmentResults = await Promise.all(userInputAttachments)       // barrier!
// NOTE: These must be created AFTER userInputAttachments completes to ensure
// nestedMemoryAttachmentTriggers is populated before getNestedMemoryAttachments runs
// ...phase 2 allThreadAttachments + phase 3 mainThreadAttachments in ONE Promise.all...
return [...user, ...thread, ...main].flat().filter(a => a !== undefined && a !== null)
```

**Flow:** bare-mode short-circuit (`CLAUDE_CODE_DISABLE_ATTACHMENTS || CLAUDE_CODE_SIMPLE` → return ONLY `getQueuedCommandAttachments(queuedCommands)` :752-761 — comment pins that query.ts dequeues unconditionally afterward, so returning [] would silently drop task-notifications Coworker depends on) → 1s abort budget over the whole sweep → three phases: (1) user-input collectors (`@file`, MCP resources, agent mentions, turn-0 skill discovery), awaited as a BARRIER because at-mention processing populates `nestedMemoryAttachmentTriggers` consumed by phase 2; (2) thread-safe collectors run for main AND subagents; (3) main-only collectors (IDE, diagnostics, token/budget usage) only when `!toolUseContext.agentId`. Each collector wrapped in `maybe()`; results flattened with a defensive `.filter(a => a !== undefined && a !== null)` (:997-1002 "a getter leaking [undefined] crashes .map(a => a.type)"). Feature gates (`feature('BUDDY')`, `TRANSCRIPT_CLASSIFIER`, `COMPACTION_REMINDERS`, `HISTORY_SNIP`) drop whole collectors via conditional spread.
**Invariant:** (1) never let a single collector throw past its `maybe()` wrapper — isolation is the whole design; (2) respect the phase-1→phase-2 ordering barrier (trigger sets); (3) queued commands must survive EVERY path including bare mode; (4) keep the total sweep under the 1s abort budget — slow probes belong in prefetches, not here.
**Probe:** no upstream test file covers this plane (`tests/` holds only shell scripts; coverage caveat). Deterministic probe: `grep -c "maybe(" src/utils/attachments.ts` → ~30 wrapped call sites; bare-mode escape pinned verbatim :752-761.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getAttachments orchestrator mainThreadAttachments allThreadAttachments", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the maybe-wrapped parallel collector pattern with phase barrier and undefined-filter; adapt which collectors exist; omit the analytics sampling if you have no telemetry. Porting trap: running thread-safe collectors before the user-input barrier reorders trigger-set population and silently drops nested-memory attachments; another trap is letting one collector's rejection reject the whole `Promise.all`.
