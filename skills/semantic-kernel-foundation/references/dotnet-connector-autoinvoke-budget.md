<!-- capsule-v2 -->
# .NET connector auto-invoke budget — unbounded for-loop gated by config, not by loop bound

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** Where does the .NET auto-invoke budget live, and does the Python streaming exhaustion asymmetry (no tool-less finale) hold in .NET?

## ClientCore.ChatCompletion loop + FunctionCallsProcessor.GetConfiguration
**Path/Symbol:** `dotnet/src/Connectors/Connectors.OpenAI/Core/ClientCore.ChatCompletion.cs:GetChatMessageContentsAsync` (lines 159–224), `GetStreamingChatMessageContentsAsync` (252–424, exhaustion gate 388–394), `GetFunctionCallingConfiguration` (1241–1291), `MaxInflightAutoInvokes` (58), `s_nonInvocableFunctionTool` (65–68); `dotnet/src/InternalUtilities/connectors/AI/FunctionCalling/FunctionCallsProcessor.cs:GetConfiguration` (90–123), `ProcessFunctionCallsAsync` (135–232), `MaximumAutoInvokeAttempts` (58), `MaxInflightAutoInvokes` (43).
**Signature:** `private ToolCallingConfig GetFunctionCallingConfiguration(Kernel? kernel, OpenAIPromptExecutionSettings executionSettings, ChatHistory chatHistory, int requestIndex)`; `public FunctionChoiceBehaviorConfiguration? GetConfiguration(FunctionChoiceBehavior? behavior, ChatHistory chatHistory, int requestIndex, Kernel? kernel)`; `public async Task<ChatMessageContent?> ProcessFunctionCallsAsync(...)`.
**Data Shape:** `ToolCallingConfig(Tools, Choice, AutoInvoke, AllowAnyRequestedKernelFunction, Options)`. Budget constants: `MaximumAutoInvokeAttempts = 128` (internal const, FunctionCallsProcessor), `MaxInflightAutoInvokes = 128` (recursion backstop, tracked in `AsyncLocal<int> s_inflightAutoInvokes`). Legacy `ToolCallBehavior` carries its own `MaximumAutoInvokeAttempts` / `MaximumUseAttempts`.

### Decisive source
```csharp
// the loop itself is UNBOUNDED — the budget lives in the per-request config
for (int requestIndex = 0; ; requestIndex++)
{
    var functionCallingConfig = this.GetFunctionCallingConfiguration(kernel, chatExecutionSettings, chatHistory, requestIndex);
    ...
    if (!functionCallingConfig.AutoInvoke || chatCompletion.ToolCalls.Count == 0)
    {
        return [chatMessageContent];   // tool-less finale IS reached on exhaustion
    }
    var lastMessage = await this.FunctionCallsProcessor.ProcessFunctionCallsAsync(...);
    if (lastMessage != null) { return [lastMessage]; }   // filter-terminate path
    this.ProcessNonFunctionToolCalls(chatCompletion.ToolCalls, chatHistory);
}

// FunctionCallsProcessor.GetConfiguration — the actual budget gate
configuration.AutoInvoke = kernel is not null && configuration.AutoInvoke;
int maximumAutoInvokeAttempts = configuration.AutoInvoke ? MaximumAutoInvokeAttempts : 0;
if (requestIndex >= maximumAutoInvokeAttempts)
{
    configuration.AutoInvoke = false;
    this._logger.LogMaximumNumberOfAutoInvocationsPerUserRequestReached(maximumAutoInvokeAttempts);
}
else if (s_inflightAutoInvokes.Value >= MaxInflightAutoInvokes)
{
    configuration.AutoInvoke = false;   // recursion backstop (AsyncLocal per async flow)
    this._logger.LogMaximumNumberOfInFlightAutoInvocationsReached(MaxInflightAutoInvokes);
}

// exhausted config still supplies a VALID request — placeholder tool keeps the service happy
return new ToolCallingConfig(
    Tools: tools ?? [s_nonInvocableFunctionTool],
    Choice: choice ?? ChatToolChoice.CreateNoneChoice(), AutoInvoke: autoInvoke, ...);
```

**Flow:** Both .NET paths (non-streaming and streaming) share one structure: an unbounded
`for (requestIndex = 0; ; requestIndex++)` whose per-iteration config comes from
`GetFunctionCallingConfiguration`. The budget is enforced INSIDE config construction: at
`requestIndex >= 128` AutoInvoke is disabled; the config still supplies tools (the
`s_nonInvocableFunctionTool` placeholder singleton) and a none-choice, so the final model call is a valid
request that the model answers WITHOUT tool calls — the loop then exits through the normal
`ToolCalls.Count == 0` return (non-streaming) or the `toolCallIdsByIndex is not { Count: > 0 }` yield-break
(streaming). So the .NET exhaustion finale IS a tool-less model call on BOTH paths. The Python streaming
asymmetry recorded in pass 6 (`for ... if not function_call_returned: return` — exhaustion ends the stream
without a finale) is therefore a Python streaming-loop property, NOT a cross-language invariant: .NET
streaming DOES get a final no-tool-call stream. Terminate path: `ProcessFunctionCallsAsync` adds the
assistant tool-call message to history, validates each call (unadvertised/unresolvable ⇒ error message
appended as the tool result, never thrown), increments `s_inflightAutoInvokes` per call, and returns
`chatHistory.Last()` when a filter sets Terminate — sequentially per call, or (concurrent mode,
`AllowConcurrentInvocation` with >1 calls) after joining ALL tasks and adding every result, stopping at the
first terminate. A second, legacy ladder exists for `ToolCallBehavior` (per-behavior
`MaximumAutoInvokeAttempts` + separate `MaximumUseAttempts` tool-advertising limit) inside the connector.
**Invariant:** The budget is a config-level gate, not a loop bound — the loop always ends through the
no-tool-calls exit, never by counter. Exhaustion still produces a well-formed final request (placeholder
tool) rather than an error. The AsyncLocal in-flight counter is a recursion backstop (a prompt function
auto-invoking itself), orthogonal to the per-request attempt budget. Every function call gets a result
message appended — success or error string — mirroring the Python corrective-feedback contract.
**Probe:** `dotnet/src/Connectors/Connectors.OpenAI.UnitTests/Core/AutoFunctionInvocationFilterTests.cs` and `AutoFunctionInvocationFilterChatClientTests.cs` (READ-ONLY — dotnet CLI broken, standing block since pass 6; tests not executed). Python contrast probe: `python/semantic_kernel/connectors/ai/chat_completion_client_base.py` streaming loop `for request_index in range(...maximum_auto_invoke_attempts): ... if not function_call_returned: return` (lines 271–289) — bounded range + silent return vs .NET unbounded for + config gate.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "GetFunctionCallingConfiguration MaximumAutoInvokeAttempts MaxInflightAutoInvokes s_nonInvocableFunctionTool ProcessFunctionCallsAsync Terminate", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: config-gated budget over an unbounded loop, the placeholder-tool exhaustion finale, and the AsyncLocal
in-flight recursion backstop. Adapt the budget constants (128/128) and the legacy ToolCallBehavior ladder to
your connector's settings surface. Omit the legacy ladder entirely if your port only supports
FunctionChoiceBehavior. NOTE for porters: the streaming exhaustion asymmetry is Python-only — do not port
the Python streaming finale behavior to .NET-shaped connectors expecting parity.
