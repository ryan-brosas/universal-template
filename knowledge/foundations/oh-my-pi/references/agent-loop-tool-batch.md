<!-- capsule-v2 -->
# Agent loop tool batch — how do you keep tool_use/tool_result pairing intact when calls never execute?

**Source:** Oh My Pi MIT `main@96f42809764f0907f7d6b115eab5710de28941de`; Codebase Memory `oh-my-pi`. **Question:** When assistant-emitted tool calls never actually run (provider stream error, abort, interrupt, token-limit stop), how does the loop keep the protocol's mandatory pairing intact without lying that the local tool failed — and when is a broken turn repaired instead?

## Single-emission executor + synthetic pairing results + transient-turn recovery
**Path/Symbol:** `packages/agent/src/agent-loop.ts` — `recoverTransientErrorToolTurn` (1937–1982); `emitToolResult` (2381–2420, `record.resultEmitted` guard); `runTool` pre-execution gates (2422–2471); shared/exclusive scheduler (2701–2727); tail sweep (2739–2749); `SyntheticToolResultDetails` taxonomy (2773–2783); `isSyntheticToolResultMessage` (2803–2810); `createSyntheticToolResultMessage` (2836–2859); `createSkippedToolResult` (2905–2935).
**Signature:** `function recoverTransientErrorToolTurn(message: AssistantMessage, availableTools: ReadonlyArray<Pick<AgentTool, "name" | "customWireName">>): AssistantMessage`; `function createSyntheticToolResultMessage(toolCall: ToolCall, reason: "aborted" | "error" | "skipped" | "length", errorMessage?: string): ToolResultMessage<SyntheticToolResultDetails>`; `emitToolResult(record, result, isError): void`.
**Data Shape:** synthetic discriminator on `details`: `{ __synthetic: true, executed: false, source: assistant_stop_aborted|assistant_stop_error|assistant_stop_skipped|assistant_stop_length|interrupt_skipped, upstreamError? }`; interrupted-after-start variant `{ __interrupted: true, execution: "started" }`.

### Decisive source
```ts
// Repair, don't lose work: a stopReason:"error" turn whose tool calls are all
// complete/known and whose error text is a TRANSIENT stream failure is restamped...
if (!AIError.isStreamReadErrorText(errorText) && !AIError.isStreamEnvelopeErrorText(errorText)
    && !AIError.isTransientStreamParseError(...)) return message;
return { ...message, stopReason: "toolUse",
    stopDetails: { type: STREAM_INTERRUPTED_AFTER_CONTENT_STOP_DETAIL, ... },
    errorMessage: undefined, errorId: undefined, errorStatus: undefined };
// ...but a call that will NEVER run still needs its pairing half. It is labeled
// "emitted, not executed" so consumers never mistake it for a local tool failure (#4321).
reason === "length" ? "…the recorded arguments are truncated and unsafe to run.
    Do NOT retry by re-emitting the same large payload — split the work…" : ...
// emitToolResult: exactly one result per record, ever.
if (record.resultEmitted) return;
// Tail sweep AFTER Promise.allSettled: the single path that gives every
// record with no message a skipped result — never inline, or you double-count.
for (const record of records) if (!record.toolResultMessage) {
    record.skipped = true;
    emitToolResult(record, createSkippedToolResult(interruptState.source, false), true);
}
```

**Flow:** batch schedules records — exclusive tools wait on the previous exclusive + all shared tasks; a throwing per-call concurrency resolver falls back to safe `"exclusive"` → `runTool` gates: pending interrupt preempts not-yet-started tools EXCEPT an `"irc"`-sourced interrupt leaves non-interruptible foreground work queued (#7493); pause gate parks before start; validation failures surface AT THE RECORD'S SLOT to keep batch order; signal-aborted ⇒ skipped + aborted result → every execution path funnels through `emitToolResult` (single emission; synthesizes `tool_execution_start` if never started) → after `Promise.allSettled`, the tail sweep pairs any remaining record with `interrupt_skipped` synthetic results → separately, at turn level, `recoverTransientErrorToolTurn` rescues complete-call turns from transient stream errors by restamping to `toolUse` + `stream_interrupted_after_content`, refusing refusal/sensitive stops and unknown-tool names.
**Invariant:** every emitted toolCall gets exactly one toolResult (real or synthetic) — providers reject orphans; synthetic results are always `isError: true` with `__synthetic`/`__interrupted` details so UI/telemetry/retry logic can distinguish "call emitted, not executed" from a real local failure; recovery only fires for ALL-known-tools complete calls on transient-text errors, never content-only turns; a completed result is never clobbered into skipped (#4752).
**Probe:** `packages/agent/test/agent-loop.test.ts:588` ("runs completed tool calls after a transient stream_read_error" ⇒ stopReason `toolUse`, stopDetails `stream_interrupted_after_content`); `:988` (synthetic result says "not executed", preserves upstream `Codex websocket transport error`, carries `__synthetic` details — the #4321 regression); `:2125` (#7493 queued non-interruptible tool still runs after an IRC interrupt aborts an earlier wait); `:1806` (#4752 keeps the completed error result instead of clobbering to skipped); `:1746` (in-flight abort vs never-executed skip distinction).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^createSyntheticToolResultMessage$|^isSyntheticToolResultMessage$|^recoverTransientErrorToolTurn$", limit: 10 });
```

## Verdict
Adopt the pairing invariant (tail-sweep single path + `resultEmitted` guard), the synthetic-result taxonomy with machine-readable `details` (never string-match prose), the length-stop split-don't-retry guidance text, IRC-vs-steering preemption asymmetry, and the narrow transient-recovery gate (complete calls + known tools + transient text only); adapt stop-detail names, error classifiers, and skip wordings to your stack; omit the Harmony partial-message discard branch unless your provider emits partial harmony frames.
