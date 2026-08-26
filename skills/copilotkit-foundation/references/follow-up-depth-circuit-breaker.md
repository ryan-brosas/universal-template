<!-- capsule-v2 -->
# Run-agent follow-up circuit breaker — how deep can recursive tool→run chains go before they must stop?

**Source:** copilotkit MIT `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** When a frontend tool requests a follow-up LLM run, what stops the recursive `processAgentResult → runAgent` loop from spinning forever?

## Depth-gated recursion guard around the follow-up branch
**Path/Symbol:** `packages/core/src/core/run-handler.ts:MAX_FOLLOW_UP_DEPTH` (:107) and `RunHandler.processAgentResult` (:674-704); depth counter `_runDepth` (:151, incremented :494, decremented in finally :566).
**Signature:** `private async processAgentResult({ runAgentResult, agent, runId?, executeFrontendTools? = true }): Promise<RunAgentResult>`
**Data Shape:** `needsFollowUp: boolean` set by `executeSpecificTool`/`executeWildcardTool` when `!handlerResult.error && tool.followUp !== false`; `_runDepth` counts nested `runAgent` frames including the current one.

### Decisive source
```typescript
const MAX_FOLLOW_UP_DEPTH = 100;
// ...
if (needsFollowUp && !this._runAbortController?.signal.aborted) {
  if (this._runDepth >= MAX_FOLLOW_UP_DEPTH) {
    logger.warn(
      `[CopilotKit] Follow-up depth limit (${MAX_FOLLOW_UP_DEPTH}) reached for agent "${agentId}". ` +
      `Stopping recursive follow-up runs to prevent an infinite loop. ` +
      // ...
    );
  } else {
    await this._internal.waitForPendingFrameworkUpdates();
    const continuationHandoff =
      this._internal.stateManager.markNextRunAsContinuation(agent, runId);
    return await this.runAgent({ agent, ...(runId !== undefined ? { runId } : {}) }, continuationHandoff);
  }
}
```

**Flow:** tools execute → any non-error result with `followUp !== false` sets `needsFollowUp` → if the shared abort controller has NOT fired, compare `_runDepth` against the cap → under the cap: yield to framework scheduler (`waitForPendingFrameworkUpdates`) so deferred React state lands BEFORE re-reading context, mark the next run as a continuation of the same logical `runId`, recurse → at/over cap: log a warning naming the remedy (`followUp: false` on the offending tool) and fall through WITHOUT recursing → `reloadSuggestions` runs either way.
**Invariant:** The cap must trip only on runaway loops (LLM repeatedly calling the same tool, backend erroring after tool results, input processors reprocessing tool messages) and never clip legitimate multi-step workflows — hence 100, deliberately high. The abort check precedes the depth check so a user stop always wins over another follow-up.
**Probe:** `packages/core/src/core/__tests__/run-handler-available.test.ts` (instantiates `createRunHandler()` through the public path); the cap itself is source-visible at :107/:682 — deterministic anchor `grep -n "MAX_FOLLOW_UP_DEPTH = 100" packages/core/src/core/run-handler.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-copilotkit", query: "processAgentResult needsFollowUp MAX_FOLLOW_UP_DEPTH", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the depth counter + absolute cap pattern for ANY tool→model recursion loop (a missing cap silently burns API quota). Adapt the threshold value and the warning text to host vocabulary. Omit nothing here — porting without the cap reproduces a documented production DOS vector (see :96-106 comment).
