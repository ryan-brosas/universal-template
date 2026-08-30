<!-- capsule-v2 -->
# Agent loop — steer safely, retain only paired work

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How can live input interrupt tool work without stealing a later follow-up or emitting invalid provider history?

## Observe steering without consuming it; dequeue only at the boundary
**Path/Symbol:** `packages/agent/src/agent-loop.ts:checkSteering` (2341–2386), `checkIrcInterrupts` (2325–2339), called from the tool-batch loop (2638, 2681, 2697).
**Signature:** `checkSteering(): Promise<void>` — mutates only abort controllers + `interruptState`.
**Data Shape:** optional `hasSteeringMessages` returning `boolean | SteeringQueueState { queued, source? }`; external `signal`, internal hard `steeringAbortController`, cooperative soft `steeringSoftController`, shared `interruptState { triggered, source }`.

### Decisive source
```ts
if (!shouldInterruptImmediately || signal?.aborted) return; // external abort ⇒ unwinding, skip
const queuedState = await hasSteeringMessages();            // observation ONLY — never drains
// boolean ⇒ source "user"; object ⇒ state.source ?? (queued ? "unknown" : undefined)
if (steeringQueued && !steeringAbortController.signal.aborted) {
  interruptState.triggered = true;
  interruptState.source = steeringSource ?? "unknown";
  steeringAbortController.abort();  // interrupts interruptible waits
  steeringSoftController.abort();   // cooperative signal for running tools
}
await checkIrcInterrupts(); // IRC fires once (interruptState.triggered); never touches a queue
```

**Flow:** poll mid-batch → non-consuming queue check → hard-abort waits + soft-signal tools → unstarted calls skipped, in-flight finish → boundary dequeues steering once.
**Invariant:** polling is non-consuming and idempotent (abort guarded by `.aborted`); a peer IRC interrupt must not re-abort after `interruptState.triggered` nor re-consume any queue.
**Probe:** direct `packages/agent/test/agent-loop.test.ts:1674` ("drains queued steering by aborting an interruptible tool mid-wait"); `:1746` distinguishes an in-flight abort from a never-executed skip.

## Normalize results before replay; retain only completed pairs
**Path/Symbol:** `agent-loop.ts:coerceToolResult` (446–512), `retainCompletedToolCalls` (1910–1938).
**Signature:** `coerceToolResult(raw): { result, malformed }`; `retainCompletedToolCalls(message, completedToolCallIds): AssistantMessage`.
**Data Shape:** unknown tool payload → typed text/image content blocks (+ invalid-block counter notes); error/aborted assistant message + completed call-ID set → filtered content.

### Decisive source
```ts
if (!Array.isArray(rawContent)) return { result: { content: [{ type: "text",
  text: "Tool returned an invalid result: missing content array." }], isError: true }, malformed: true };
const isError = explicitError || invalidBlocks > 0 || providerMetadataResult.malformed;
// Anthropic rejects tool_result blocks with is_error: true and empty content.
if (isError && !hasSubstantiveToolResultContent(content)) {
  content.length = 0;
  content.push({ type: "text", text: EMPTY_ERROR_TOOL_RESULT_TEXT }); // "Tool failed with no output." (:436)
}
```
```ts
if (message.stopReason !== "error" && message.stopReason !== "aborted") return message;
const content = message.content.filter(b => b.type !== "toolCall" || completedToolCallIds.has(b.id));
// stopDetails restamped to STREAM_INTERRUPTED_AFTER_CONTENT_STOP_DETAIL unless already so
```

**Flow:** validate unknown blocks → make errors substantive/non-empty → attach result to call ID → on stopReason error/aborted drop unfinished call declarations so replay stays provider-valid.
**Invariant:** every retained result has its declared call; malformed error output is serializable and non-empty.
**Probe:** direct `agent-loop.test.ts:727` recovers only completed calls after a parse-error interruption; `:4621–4655` fills whitespace-only error output with `"Tool failed with no output."`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(checkSteering|coerceToolResult|executeToolCalls|retainCompletedToolCalls)$", limit: 8, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.agent.src.agent-loop.checkSteering" });
```

## Verdict
Adopt non-consuming interrupt polling with a hard/soft two-controller ladder and completed-only result retention; adapt queue-state/source typing and stop-detail stamping to host stream events; omit IRC-specific peer-interrupt plumbing unless porting that transport. Coverage caveat: tests excluded from graph index by design; probes are source-grounded from on-disk test files.
