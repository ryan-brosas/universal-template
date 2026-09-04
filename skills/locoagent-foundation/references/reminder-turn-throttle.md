<!-- capsule-v2 -->
# Human-turn throttle counters — why do reminder intervals fire every N human turns and not every N tool rounds?

**Source:** locoagent (Claude Code CLI fork, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** the shared backward-scan idiom that keeps nags from firing 20× inside one agentic turn.

## getPlanModeAttachmentTurnCount / getAutoModeAttachmentTurnCount
**Path/Symbol:** `src/utils/attachments.ts:getPlanModeAttachmentTurnCount` (:1131-1163), `getAutoModeAttachmentTurnCount` (:1275-1313), `countPlanModeAttachmentsSinceLastExit` (:1169-1184), `countAutoModeAttachmentsSinceLastExit` (:1319-1333), `getVerifyPlanReminderTurnCount` (:3872-3889).
**Signature:** `(messages: Message[]) → { turnCount, foundXAttachment }`; exit-counters return plain numbers.
**Data Shape:** backward iteration over the transcript; "human turn" = `type === 'user' && !isMeta && !hasToolResultContent(content)`; stop at the first matching attachment (or its `_exit` counterpart).

### Decisive source
```ts
// Iterate backwards to find most recent plan_mode attachment.
// Count HUMAN turns (non-meta, non-tool-result user messages), not assistant
// messages — the tool loop in query.ts calls getAttachmentMessages on every
// tool round, so counting assistant messages would fire the reminder every
// 5 tool calls instead of every 5 human turns.
for (let i = messages.length - 1; i >= 0; i--) {
  const message = messages[i]
  if (message?.type === 'user' && !message.isMeta &&
      !hasToolResultContent(message.message.content)) turnsSinceLastAttachment++
  else if (attachment of matching type) { found = true; break }
}
```

**Flow:** collector gate: if a prior attachment exists AND `turnCount < CONFIG.TURNS_BETWEEN_ATTACHMENTS` → skip. First-ever turn always attaches (`found === false` bypasses the throttle). Full/sparse cadence is separate: `countSinceLastExit(messages) + 1 % FULL_REMINDER_EVERY_N === 1` → 'full'; the exit-attachment sentinel RESTARTS both cycles on re-entry. Auto-mode's scanner additionally breaks on `auto_mode_exit` to reset the throttle. Verify-plan's counter stops at `plan_mode_exit` ("marks when implementation started") returning 0 when absent.
**Invariant:** NEVER count assistant/tool-loop messages — the tool loop invokes collection every round, so any assistant-counting interval collapses to per-tool-call nagging ("60-105× per session" observed in auto mode). Tool-result user messages must be excluded via content inspection, NOT `toolUseResult === undefined`: sub-agent tool results explicitly set it to undefined for Explore agents (:2441-2449 comment). Exit attachments are state sentinels — scanning must treat them as cycle boundaries.
**Probe:** no upstream test (coverage caveat). Deterministic probe: the decisive comment block pinned verbatim at :1138-1142 and :1282-1287; `grep -n "isHumanTurn\|hasToolResultContent" src/utils/attachments.ts`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "turn count plan_mode auto_mode reminder throttle", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the human-turn definition + backward-scan-with-sentinel pattern for ANY recurring injection; adapt thresholds; omit plan/auto specifics. Porting trap: counting assistant messages or forgetting the tool-result-content check makes every interval ~50× tighter than designed in agentic sessions.
