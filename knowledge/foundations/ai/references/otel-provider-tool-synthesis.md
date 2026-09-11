<!-- capsule-v2 -->
# otel provider-executed tool synthesis — reconstructing execute_tool spans the runtime never emitted

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai`. **Question:** How do you trace tools executed INSIDE the model provider (MCP/code-execution) when no `onToolExecutionStart/End` events ever fire for them?

## Path/Symbol
`packages/otel/src/open-telemetry.ts:onLanguageModelCallEnd` (:754–911) — `inferenceToolDefinitions` captured at call start (:687), `hasObservedProviderTools` (:765), `finalToolOutputs` map (:837–851), `recordedToolCallIds` set (:853).

**Signature:** synthesis consumes `event.content` parts of types `tool-call` / `tool-result` / `tool-error` filtered by `part.providerExecuted === true`; spans named `` `execute_tool ${part.toolName}` `` under `state.inferenceContext`.

**Data Shape:** observed definitions extend the declared tool list with `{type:'extension', name}` entries; results keyed by toolCallId with preliminary-vs-final distinction.

### Decisive source
```ts
    const finalToolOutputs = new Map<
      string,
      Extract<
        (typeof event.content)[number],
        { type: 'tool-result' | 'tool-error' }
      >
    >();
    for (const part of event.content) {
      if (
        part.type === 'tool-error' ||
        (part.type === 'tool-result' && part.preliminary !== true)
      ) {
        finalToolOutputs.set(part.toolCallId, part);
      }
    }
```
(:837–851; span creation loop :853–905 dedupes via recordedToolCallIds and ends each span immediately)

**Flow:** at CALL START, declared tools are stashed (`state.inferenceToolDefinitions = event.tools` :687). At CALL END: (a) any provider-executed tool-call whose toolName is NOT in the declared set gets a synthetic `{type:'extension'}` definition appended (:776–781) and flips `hasObservedProviderTools`, which re-serializes the WHOLE definitions attribute (:817–821); (b) final outputs indexed per toolCallId — `preliminary: true` results (streaming placeholders like "running") are skipped so only terminal state lands on the span; (c) one INTERNAL `execute_tool <name>` span per unique provider-executed callId is created under the chat span's context (:884), gets `gen_ai.tool.type:'extension'` + arguments, then result or `recordErrorOnSpan` (:901), then `.end()` synchronously. Client-side tools instead use the REAL `onToolExecutionStart/End` pair (:913–989) where `gen_ai.tool.type` = `'extension' | 'function'` by the same flag and duration comes from `event.toolExecutionMs`.

**Invariant:** (1) Deferred results are not lost: a call that arrives before its result STILL gets its (result-less) span now — pinned by test "keeps deferred provider tool calls visible before their result arrives" (:1026–1094) which asserts exactly ONE execute_tool span exists after the follow-up step delivers the result into output messages instead. (2) The extension definition is appended ONLY when un-declared (`definedToolNames.has(part.toolName)` skip :771) and the definitions attribute re-emitted only when something was observed — otherwise start-time serialization stands. (3) Synthesized spans are fire-and-forget: they can never outlive the chat span because they're created and ended inside CallEnd. (4) Errors take the error path exclusively — result AND status ERROR never coexist (test :989 asserts `gen_ai.tool.call.result` undefined + exceptions length 1).

**Probe:** `grep -c "type: 'extension'" packages/otel/src/open-telemetry.ts` → 1 (definition literal; span-side value is `'extension'` string in attributes). `grep -n "preliminary !== true" packages/otel/src/open-telemetry.ts` → :847. `grep -n "hasObservedProviderTools" packages/otel/src/open-telemetry.ts` → :765/:781/:817. Direct tests: open-telemetry.test.ts :854 (results+observed definitions incl. exact `gen_ai.tool.definitions` snapshot), :949 ("records only the final provider-executed tool result" → `{"value":2}`), :989 (error path).

**Retrieve:** live-resolved @pin:
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "OpenTelemetry executeLanguageModelCall inferenceContext", limit: 3 });
// → otel open-telemetry.OpenTelemetry.executeLanguageModelCall 185-200 (rank-1)
```

**Verdict:** ADOPT — mandatory pattern whenever a gateway/provider executes tools server-side.
