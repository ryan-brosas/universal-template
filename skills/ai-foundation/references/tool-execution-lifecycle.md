<!-- capsule-v2 -->
# Tool execution lifecycle — how does a single tool call run with callbacks, streaming outputs, timeouts, and error capture without any throw escaping?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How do per-tool timeout, outer abort signal, start/end callbacks, and preliminary results compose into one execution whose failures become data instead of exceptions?

## executeToolCall
**Path/Symbol:** `packages/ai/src/generate-text/execute-tool-call.ts:43-223` (`executeToolCall`).
**Signature:** `executeToolCall({toolCall, tools?, callId, messages, abortSignal?, timeout?: TimeoutConfiguration<TOOLS>, experimental_sandbox?, onPreliminaryToolResult?, onToolExecutionStart?: Arrayable<cb>, onToolExecutionEnd?: Arrayable<cb>, executeToolInTelemetryContext? = async ({execute}) => await execute(), runInTracingChannelSpan? = pass-through}): Promise<{output: ToolOutput | TypedToolError, toolExecutionMs} | undefined>`.
**Data Shape:** Returns `undefined` when the tool has no `execute` (provider-executed only). Success ⇒ `{type:'tool-result', toolCallId, toolName, input, output, dynamic, providerMetadata?, toolMetadata?}`; failure ⇒ same shape but `{type:'tool-error', error}` — both carry `toolExecutionMs`.

### Decisive source
```ts
if (!isExecutableTool(tool)) return undefined;           // no-execute ⇒ undefined, NOT an error
const context = await validateToolContext({              // TypeValidationError on bad context
  toolName, context: getOwn(toolsContext, toolName), contextSchema: tool.contextSchema });
await notify({ event: baseCallbackEvent, callbacks: onToolExecutionStart }); // awaited, swallow-errors

const toolTimeoutMs = getToolTimeoutMs(timeout, toolName); // {tools:{[name+'Ms']}} ?? toolMs; number-form ⇒ undefined
const toolAbortSignal = mergeAbortSignals(abortSignal, toolTimeoutMs);     // undefined when BOTH absent

try {
  const stream = executeTool({ tool, input, options: { toolCallId, messages,
    abortSignal: toolAbortSignal, context, experimental_sandbox: sandbox } });
  for await (const part of stream) {
    if (part.type === 'preliminary') {
      onPreliminaryToolResult?.({ ...toolCall, type: 'tool-result',
        output: part.output, preliminary: true });       // partial output fan-out
    } else {
      output = part.output;                              // last final part wins
    }
  }
} catch (error) {
  const toolError = { type: 'tool-error', toolCallId, toolName, input, error,
    dynamic: tool.type === 'dynamic', /* +providerMetadata/toolMetadata if present */ };
  await notify({ event: { ...baseCallbackEvent, toolOutput: toolError, toolExecutionMs },
    callbacks: onToolExecutionEnd });
  return { output: toolError, toolExecutionMs };         // exception becomes DATA
}
// success path: same end-callback notify with toolResult, then return it.
```

**Flow:** executable-check → context validation → tracing-span wrap → `onToolExecutionStart` (parallel, awaited, errors swallowed) → timeout+signal merge → telemetry-context wrapper (keeps nested AI SDK calls associated with THIS tool execution; timing stays inside the inner `execute`) → stream consumption (`preliminary` parts fan out live, final sets `output`) → terminal branch: `tool-result` or `tool-error`, each announced via `onToolExecutionEnd` and returned.

**Invariant:** Execution errors NEVER propagate — they return as `{type:'tool-error'}` output so the step loop records a result for every call; `toolExecutionMs` measures ONLY the inner execute (set in the inner `finally`), not callback overhead. Callbacks are fire-and-forget-safe: `notify` runs them in parallel with per-callback try/catch, so a throwing callback can neither break execution nor leak rejections. Timeout signal exists ONLY when a tool-level timeout resolves — number-form `timeout` does NOT reach tools (test-pinned).

**Probe:** `packages/ai/src/generate-text/execute-tool-call.test.ts:44` (no execute ⇒ undefined), `:211` (execution failure returns tool-error), `:357/:503/:527` (throwing start/end callbacks don't break flow), `:956` (toolMs set ⇒ tool receives an un-aborted signal), `:981` (no timeout ⇒ `abortSignal === undefined` inside tool), `:1004` (merged signal `!== controller.signal` but present), `:1031` (per-tool `testToolMs: 2000` overrides `toolMs: 10000`), `:869` (duration measured around inner execute only).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "executeToolCall onToolExecutionEnd tool-error", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the whole lifecycle: undefined-for-no-execute, error-as-data terminal shape, parallel swallowed callbacks, merged timeout+abort signal, preliminary-result channel, inner-scoped duration metric. Adapt the telemetry/tracing-channel wrapper hooks to host observability. Omit sandbox session plumbing unless porting sandboxed execution.
