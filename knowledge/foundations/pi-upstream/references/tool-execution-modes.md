<!-- capsule-v2 -->
# Tool execution modes — how do you run a batch of tool calls concurrently without corrupting result order or abort safety?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter wants parallel tool calls — what must stay sequential, and in which order do results land?

## Prepare sequentially, execute in parallel, persist in source order
**Path/Symbol:** `packages/agent/src/agent-loop.ts:411-426` (`executeToolCalls` mode dispatch), `:489-554` (`executeToolCallsParallel`), `:600-668` (`prepareToolCall`), `:582-584` (`shouldTerminateToolBatch`).
**Signature:** dispatch: `executionMode === "sequential"` on config OR ANY call's tool declares `executionMode: "sequential"` → sequential path. Parallel path collects `FinalizedToolCallEntry = FinalizedToolCallOutcome | (() => Promise<FinalizedToolCallOutcome>)`.
**Data Shape:** Sequential = one loop, abort-checked between calls. Parallel = immediate outcomes (not-found / blocked / aborted / validation-error) stored as values; real executions stored as thunks; ONE `Promise.all` runs the thunks; results are then emitted and persisted in SOURCE order.

### Decisive source
```ts
const orderedFinalizedCalls = await Promise.all(
	finalizedCalls.map((entry) => (typeof entry === "function" ? entry() : Promise.resolve(entry))),
);
const messages: ToolResultMessage[] = [];
for (const finalized of orderedFinalizedCalls) {   // source order preserved
	const toolResultMessage = createToolResultMessage(finalized);
	await emitToolResultMessage(toolResultMessage, emit);
	messages.push(toolResultMessage);
}
return { messages, terminate: shouldTerminateToolBatch(orderedFinalizedCalls) };
// shouldTerminateToolBatch: every(call => call.result.terminate === true) — unanimity
```

**Flow:** per-call `tool_execution_start` (in submission order) → prepare (resolve tool → prepareArguments → validateToolArguments → beforeToolCall gate w/ block+terminate) → immediate outcome OR thunk → concurrent execution with per-call partial-result updates → `tool_execution_end` events fire in COMPLETION order (test-pinned) but toolResult messages are emitted/persisted after the join, in source order → terminate only if every result set `terminate === true` (a mixed batch continues).
**Invariant:** (1) Preparation/validation is sequential; only execution is parallel — beforeToolCall gates see args in deterministic order. (2) Provider-visible history order always matches the assistant message's call order regardless of completion timing. (3) One `sequential`-mode tool forces the whole batch sequential. (4) Terminate requires unanimity.
**Probe:** `packages/agent/test/agent-loop.test.ts:787/:870/:957` (executionMode forcing), `:586` ("emit tool_execution_end in completion order but persist tool results in source order"), `:1201-1436` (terminate unanimity incl. blocked-with-terminate + mixed batches).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "executeToolCallsParallel orderedFinalizedCalls", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt prepare-sequential/execute-parallel with source-order persistence and terminate-unanimity. Adapt the executionMode vocabulary to your tool schema. Omit the thunk/value union if your host has no synchronous immediate outcomes. Coverage caveat: none — this plane is the most densely test-pinned file in the package.
