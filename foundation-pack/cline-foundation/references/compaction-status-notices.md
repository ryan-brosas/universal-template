<!-- capsule-v2 -->
# Compaction status notices — the started/completed/skipped event contract

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `ext-cline`. **Question:** What must a host emit so UIs can show compaction progress, and how do mode prefixes compose?

## Prefix × phase matrix with budget-adjustment side channel
**Path/Symbol:** `sdk/packages/core/src/extensions/context/compaction.ts:397-418` (started), `559-614` (completed + `compaction-budget-adjusted`), `615-637` (skipped).
**Signature:** `emitStatusNotice(message: `${prefix}compacting|compacted|compaction-skipped`, metadata)` with prefix `""|"auto-"|"overflow-recovery-"` by mode.
**Data Shape:** metadata carries `{kind, reason, phase:"started"|"completed"|"skipped", iteration, triggerTokens/targetTokens or tokensBefore/tokensAfter, messagesBefore/After, maxInputTokens}`.

### Decisive source
```ts
const noticePrefix =
    effectiveMode === "manual"
        ? ""
        : effectiveMode === "overflow_recovery"
            ? "overflow-recovery-"
            : "auto-";
context.emitStatusNotice?.(`${noticePrefix}compacting`, { ... phase: "started", ... });
```

**Flow:** manual mode emits UNPREFIXED notices (`compacting`, `compacted`) — the user asked for it, no attribution needed; auto/overflow get prefixed variants. A result whose budget projection took emergency actions (actionCount>0 || warningCount>0) additionally emits `compaction-budget-adjusted` + telemetry `task.compaction_budget_emergency`; skipped results still emit a skipped notice + `task.compaction_skipped` telemetry. Telemetry ulid = host sessionId ?? conversationId, tagged agentId/conversationId/parentAgentId for multi-agent attribution.
**Invariant:** Known gap documented in-source: compactions via plugin `registerMessageBuilder()` or `beforeModel` hooks bypass this wrapper entirely and emit NO telemetry — porters adding hook-path compaction must instrument separately.
**Probe:** `grep -cF 'compaction-budget-adjusted' sdk/packages/core/src/extensions/context/compaction.ts` → 1; upstream suite asserts notice sequences around every strategy test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cline", query: "emitStatusNotice compacting", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the prefix×phase naming scheme and the budget-emergency side channel; adapt event transport; keep the documented telemetry gap in mind when wiring alternate entrypoints. Runner blocked honestly; battery greps green.
