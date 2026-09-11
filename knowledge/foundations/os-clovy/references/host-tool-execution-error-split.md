<!-- capsule-v2 -->
# Host-tool execution error split — when is a tool failure terminal and when must the model self-correct?

**Source:** os-clovy MIT `main@8fed7acb51622d36bfaaa056f43931015dfd5d72`; Codebase Memory `os-clovy`. **Question:** A porter wiring SDK tools to a host RPC boundary must decide which execution failures kill the run, which go back to the model as feedback, and what each emits.

## Reserved `tool.invoke` execution plane
**Path/Symbol:** `agent-runtime/src/sdk-engine.ts:OpenAIAgentsEngine.createTool` (:241-309), `AgentToolExecutionError` (:48-62), `hostAppErrorCode` (:448-451); `types.HostToolInvoker` (types.ts :221-228). `invokeHostTool` (:76, wired in `main.ts` :9-21) routes EVERY host callback — tools AND the model provider (`createModelProvider` :420-445) — through one `peer.request("tool.invoke", ...)`.
**Signature:** `private createTool(descriptor, sessionId, runId, emit): FunctionTool`; invoker `(input: {sessionId, runId, name, arguments, callId, signal?}) => Promise<JsonValue>`.
**Data Shape:** `AgentToolExecutionError` carries `failureCategory: "tool"|"credits"`, `failureCode: "agent_tool_failed"|"agent_credits_required"`, `retryable=false`. Credit detection: `/insufficient[_ -]?credits|credit balance|balance is too low/i` over `${appErrorCode ?? ""} ${message}`. `hostAppErrorCode` reads `error.data.appErrorCode` off the transport `ProtocolError`.

### Decisive source
```ts
// errorFunction: HOST failures are terminal; model argument mistakes stay model-visible
errorFunction: (_context, error) => {
  if (error instanceof AgentToolExecutionError) throw error;      // rethrow → SDK aborts run
  const details = error instanceof Error ? error.toString() : String(error);
  return `An error occurred while running the tool. Please try again. Error: ${details}`;
},
execute: async (argumentsValue, _context, details) => {
  const callId = toolCallId(details);
  emit({ type: "tool.started", callId, name, arguments: sanitizeForLog(argumentsJson) });
  try {
    const output = await this.invokeHostTool({ sessionId, runId, name, arguments, callId });
    emit({ type: "tool.completed", callId, name, output: sanitizeForLog(output) });
    return output;
  } catch (error) {
    emit({ type: "tool.failed", callId, name, error: "Tool execution failed." }); // GENERIC
    throw new AgentToolExecutionError(message, hostAppErrorCode(error));
  }
}
```

**Flow:** model emits tool call → strict schema validation (invalid JSON arguments are rejected BEFORE execute; test proves they never reach the host) → `tool.started` (sanitized args) → host round-trip → success: sanitized output to event AND return value → failure: `errorMessage(error)` becomes the AgentToolExecutionError message, but the EVENT carries only `"Tool execution failed."` → errorFunction rethrows the tagged error → run settles via `runtimeFailureDetails` as `{category, code, retryable:false}`.
**Invariant:** Host/transport failures are ALWAYS terminal and NEVER leak their raw text into events (test asserts `!JSON.stringify(events).includes("tool transport failed")`); credit classification survives from the host's `appErrorCode`; the generic `tool.failed` string is a fixed constant so hostile output cannot ride the event channel; model-generated schema violations consume zero host calls.
**Probe:** `agent-runtime/test/sdk-tool-loop.test.ts` — "surfaces a host tool exception as a terminal tagged failure" (:222-293, asserts category/code + raw-string absence), "preserves credit classification from a native host tool failure" (:295-362), "returns invalid model tool arguments for self-correction" (:364-448, asserts `hostToolCalls === 0` then a corrected second turn). Suite runner-blocked at pin (@openai/agents absent); names/ranges read directly.
## Get live surrounding code
**Retrieve:** executed at pin (top hits = target family):
```
search_graph({ project:"os-clovy", query:"reserved host tool invoke callback execute", file_pattern:"agent-runtime/*" })
→ src.types.HostToolInvoker Type types.ts 221-228
   src.sdk-engine.OpenAIAgentsEngine.createTool Method sdk-engine.ts 241-309
   src.sdk-engine.AgentToolExecutionError Class sdk-engine.ts 48-62
```

## Verdict
Adopt the two-lane error split (tagged terminal error vs model-visible correction string), the fixed generic `tool.failed` event text, and appErrorCode-driven credit classification — this trio is what keeps hostile tool output out of the event stream while preserving UI-actionable taxonomy. Adapt the credit regex vocabulary and the reserved method name to your protocol. Omit nothing structural; note that `invokeHostTool` being shared by tools AND the model provider is what makes "zero direct HTTP in the runtime" enforceable.
