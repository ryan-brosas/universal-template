<!-- capsule-v2 -->
# Harness turn telemetry shim — how does a non-streamText turn fire the AI SDK Telemetry lifecycle that `@ai-sdk/otel` requires?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** Your agent runtime has no language-model call, no standardized prompt, no sampling settings — yet your OTel integration only emits spans when the FULL generateText/streamText event lifecycle fires. What do you map, what do you fake, and what do you leave undefined?

## Turn→operation mapping with lazy step synthesis and a NOOP opt-in gate

**Path/Symbol:** `packages/harness/src/agent/internal/turn-telemetry.ts` — header rationale (:5–21), `NOOP` (:82–93), `createTurnTelemetry` (:158–489: `fireStart` :205–228, `start` :230–234, `ensureStepOpen` :236–267, `inferenceEnd` :270–296, `closeOpenTools` :313–333, `stepFinish` :339–371, `toolStart/toolEnd` :373–421, `end` :423–479, `error` :481–487); dispatcher drive sites in run-prompt.ts (:527 start, :635 runtime-resolved modelId, :645 ensureStepOpen per non-boundary part, :338/:365 stepFinish/end, :1055 error).
**Signature:** `createTurnTelemetry({telemetry, harnessId, modelId?, instructions?, promptText, runtimeContext}): TurnTelemetry`; mapping = turn→operation `operationId:'ai.harness'`, each finish-step→onStepStart+onLanguageModelCallStart…End+onStepEnd, tool-call→onToolExecutionStart/End.
**Data Shape:** latches `started/stepOpen/ended`, counter `stepNumber`, `openTools: Map<toolCallId, call>`; model-call-only fields (sampling params, toolsContext, performance timings) sent as `undefined` / zero-filled.

### Decisive source
```ts
// :158–160 — opt-in gate: no telemetry settings ⇒ NOOP singleton, zero work, no events
if (opts.telemetry == null) return NOOP;
// :632–645 (run-prompt) — operation span opens on stream-start with the RUNTIME-RESOLVED model
await telemetry.start(value.modelId ?? input.session.modelId);
// ensureStepOpen fires lazily before first content of a step:
if (!started) await fireStart();
... await dispatcher.onStepStart?.(...stepNumber...);
await dispatcher.onLanguageModelCallStart?.({ callId, provider, modelId, messages: inputMessages });
// :423+ end() — synthesizes the missing close when the turn dies mid-step:
if (stepOpen) {
  await closeOpenTools();   // every open tool ends with {type:'error', error: Error('tool span unclosed')}
  await inferenceEnd({ finishReason, usage, content: [] });
  await dispatcher.onStepEnd?.({...});  stepOpen = false;
}
ended = true; await dispatcher.onEnd?.({ ..., text: finalStepText, toolCalls: outputToolCalls, ... });
```

**Flow:** runPrompt creates the shim once per turn → stream-start fires `start` (first call wins; runtime model overrides configured id) → every non-boundary part calls `ensureStepOpen` → finish-step closes the step triple and bumps stepNumber → tool calls open/close deduped by toolCallId (`toolEnd` no-ops for unknown ids so provider-executed and host-executed paths can BOTH call it) → terminal finish/error closes everything exactly once.
**Invariant:** The integrations' real fields (`callId`, `operationId`, `provider='harness:<id>'`, `modelId`, `messages=[{role:'user',content:promptText}]`, `toolCall`, normalized usage/finishReason) carry true values while unknowable fields stay honestly undefined; every lifecycle method is idempotent under replay; an unclosed tool span can never dangle — it terminates as an explicit error output at step/turn end.
**Probe:** direct test `turn-telemetry.test.ts:16–53` pins step-number sequencing across two steps (`stepStartNumbers [0,1]`, `stepEndNumbers [0,1]`) — executed read-verified @pin (runner block stands: vitest unavailable). Deterministic content probes: NOOP gate line :159, `'tool span unclosed'` literal :329, `operationId:'ai.harness'` :212/:443 all byte-exact.
**Retrieve:** `search_graph { project:"ai", query:"telemetry dispatcher operation span turn lifecycle", limit:3 }` → rank#1 ai-core `runInTracingChannelSpan`, rank#2 harness `Dispatcher Type :23`, rank#3 `createTelemetryDispatcher :67–209` — placing the shim's dispatcher type directly beside the shared kernel it drives (verified live @pin); trace_path inbound `createTurnTelemetry` → callers_total=3 (HarnessAgentSession.promptTurn/continueTurn hop-2, runPrompt hop-1).

## Get live surrounding code
```ts
await mcp.codebase_memory.get_code_snippet({ project: "ai", qualified_name: "ai.packages.harness.src.agent.internal.turn-telemetry.createTurnTelemetry" });
```

## Verdict
Adopt the lifecycle-shim shape when any consumer requires the standard generate/stream telemetry contract from a foreign executor; adapt the field table to what your runtime truly knows; omit the synthesized-step close only if your turns always end on clean boundaries (then mid-step death must still close open tools).
