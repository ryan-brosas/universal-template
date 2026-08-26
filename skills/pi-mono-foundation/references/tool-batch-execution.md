<!-- capsule-v2 -->
# Tool batch execution — how does a batch of assistant tool calls run safely across parallel and sequential modes without corrupting result order or losing termination?

**Source:** pi-mono MIT `main@80e62761f7251a104f1b21d9c73920c720f0ec00`; Codebase Memory `pi-mono`. **Question:** How do I execute a mixed batch of model-requested tool calls with validation failures, blocking hooks, aborts, and per-tool sequential constraints while preserving the model's call order?

## Fan-out plane in the agent loop
**Path/Symbol:** `packages/agent/src/agent-loop.ts:executeToolCalls` (:411-426), `executeToolCallsSequential` (:433-487), `executeToolCallsParallel` (:489-554), `shouldTerminateToolBatch` (:582-584), `prepareToolCall` (:600-650+); `packages/ai/src/utils/validation.ts:validateToolArguments` (:317-350).
**Signature:** `executeToolCalls(ctx, assistantMessage, config, signal, emit): Promise<{messages: ToolResultMessage[], terminate: boolean}>`
**Data Shape:** batch = all `toolCall` blocks of ONE assistant message; outcomes carry `{toolCall, result, isError}`; `FinalizedToolCallEntry = FinalizedToolCallOutcome | (() => Promise<Outcome>)`.

### Decisive source
```ts
// dispatch — one sequential tool serializes the WHOLE batch
const hasSequentialToolCall = toolCalls.some(
    (tc) => currentContext.tools?.find((t) => t.name === tc.name)?.executionMode === "sequential",
);
if (config.toolExecution === "sequential" || hasSequentialToolCall) return executeToolCallsSequential(...);
// parallel — positional entries keep the model's order under Promise.all
finalizedCalls.push(async () => { const executed = await executePreparedToolCall(...); ... });
...
const orderedFinalizedCalls = await Promise.all(
    finalizedCalls.map((entry) => (typeof entry === "function" ? entry() : Promise.resolve(entry))),
);
```

**Flow:** filter batch → mode election → per call: emit `tool_execution_start` → `prepareToolCall` resolves unknown-tool / validation failure / `beforeToolCall` block / abort into an immediate error outcome (never a throw into the loop) → execute + finalize (`finalizeExecutedToolCall`) → emit end, build one `ToolResultMessage` per outcome → parallel mode awaits all then emits results in ORIGINAL order; both modes break the preparation loop on `signal.aborted`; `terminate` is true only when the non-empty batch is ALL-terminate.
**Invariant:** tool-result messages appear in exactly the assistant message's toolCall order regardless of completion order; a failed validation becomes an error `toolResult` fed back to the model (`validateToolArguments` clones args, coerces optional-nulls and JSON-Schema types, throws only a formatted message that prepare converts to an immediate outcome); abort never skips already-completed results.
**Probe:** `packages/agent/test/e2e.test.ts:62-100` pins `pendingToolCalls` lifecycle around `tool_execution_start/end` events; `:102-128` pins aborted stopReason propagation. Both direct-read this pass. Live suite note: full agent package suite ran GREEN in pass 1 (47 tests incl. agent-loop); e2e file itself imports generated model data in some fixtures — treat per-model e2e variants as fixture-blocked.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-mono", query: "tool calls execution batch parallel sequential validate arguments stop reason", limit: 20 });
// executed live this pass: ranked executeToolCallsSequential :433-487 (#1), executeToolCallsParallel :489-554 (#2),
// validateToolArguments :317-350 (#3); trace_path inbound on executeToolCallsParallel → {executeToolCalls, runLoop}
```

## Verdict
Adopt: positional-entry parallelism with ordered emission, whole-batch serialization on any sequential tool, immediate-outcome funnel for pre-execution failures, all-terminate semantics. Adapt the validation coercion depth to your schema library. Omit the specific event vocabulary if your host differs. Coverage: `no_recorded_issue` ×2 cited source paths at generation 2026-08-24T16:11:21Z.
