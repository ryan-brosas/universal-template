<!-- capsule-v2 -->
# Function-choice behavior .NET twin — settings-prep wrapper and the shared fail-early selection contract

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** What does the experimental settings-prep wrapper actually do, and which FunctionChoiceBehavior invariants are shared between the Python and .NET twins?

## prepare_settings_for_function_calling + .NET FunctionChoiceBehavior
**Path/Symbol:** `python/semantic_kernel/connectors/ai/function_calling_utils.py:prepare_settings_for_function_calling` (lines 161–191); `dotnet/src/SemanticKernel.Abstractions/AI/FunctionChoiceBehaviors/FunctionChoiceBehavior.cs` (whole file, 177 lines: factories 66–113, `GetConfiguration` 116–118, `GetFunctions` 120–177).
**Signature:** `def prepare_settings_for_function_calling(settings: "PromptExecutionSettings", settings_class: type["PromptExecutionSettings"], update_settings_callback: Callable[..., None], kernel: "Kernel") -> "PromptExecutionSettings"`; .NET: `public static FunctionChoiceBehavior Auto(IEnumerable<KernelFunction>? functions = null, bool autoInvoke = true, FunctionChoiceBehaviorOptions? options = null)` (+ `Required`, `None`), `protected IReadOnlyList<KernelFunction>? GetFunctions(IList<string>? functionFQNs, Kernel? kernel, bool autoInvoke)`.
**Data Shape:** Python: behavior carries `filters` (dict, four keys, hyphen-joined FQNs) + `maximum_auto_invoke_attempts` (Auto→5, Required→1, NoneInvoke→0). .NET: behavior carries explicit `IEnumerable<KernelFunction>?` instances + `autoInvoke` + `FunctionChoiceBehaviorOptions`; JSON-polymorphic with `"type"` discriminator (auto/required/none).

### Decisive source
```python
# Python wrapper: deepcopy -> convert -> configure-only-if-behavior
settings = deepcopy(settings)
if not isinstance(settings, settings_class):
    settings = settings_class.from_prompt_execution_settings(settings)
if settings.function_choice_behavior:
    settings.function_choice_behavior.configure(
        kernel=kernel, update_settings_callback=update_settings_callback, settings=settings)
return settings
```

```csharp
// .NET selection: fail early BEFORE any model round-trip
if (autoInvoke && kernel is null)
    throw new KernelException("Auto-invocation is not supported when no kernel is provided.");
...
if (functionFQNs is { Count: > 0 })
{
    foreach (var functionFQN in functionFQNs)
    {
        var nameParts = FunctionName.Parse(functionFQN, FunctionNameSeparator);  // "." separator
        if (kernel is not null && kernel.Plugins.TryGetFunction(nameParts.PluginName, nameParts.Name, out var function))
        { availableFunctions.Add(function); continue; }
        if (autoInvoke)
            throw new KernelException($"The specified function {functionFQN} is not available in the kernel.");
        function = this._functions?.FirstOrDefault(f => f.Name == nameParts.Name && f.PluginName == nameParts.PluginName);
        if (function is not null) { availableFunctions.Add(function); continue; }
        throw new KernelException($"The specified function {functionFQN} was not found.");
    }
}
else if (functionFQNs is { Count: 0 }) { return availableFunctions; }        // empty list = disable
else if (kernel is not null) { /* null list = ALL plugin functions flattened */ }
```

**Flow:** The Python wrapper is the shared entry every connector uses before a request:
deepcopy (never mutate the caller's settings), convert to the service's own settings class when
needed, then call `configure()` ONLY when a behavior is present — a `None` behavior means the
settings pass through unconfigured (no tools installed). The .NET twin inverts the selection
model: instead of dict filters resolved at configure time, callers pass KernelFunction instances
up front, and `GetFunctions` resolves an FQN list against the kernel with a strict ladder —
autoInvoke with no kernel throws immediately; a listed function missing from the kernel throws
when autoInvoke (fail early rather than advertise something uninvokable), otherwise falls back to
the constructor-provided instances; an EMPTY FQN list disables function calling; a NULL list
advertises every function of every plugin. Python's budget lives on the behavior
(`maximum_auto_invoke_attempts`); .NET's lives in the connector-side configuration the behavior's
`GetConfiguration` hands back.
**Invariant:** Both twins share the fail-early contract: never advertise a function the runtime
cannot invoke — Python proves it at the agent plane (`_validate_function_tools_registered` raises
before run creation) and at template/registry lookup time; .NET proves it inside `GetFunctions`
before the first request. Both also share "null/absent selection = everything, empty selection =
nothing" semantics (Python: filters None → full metadata list; .NET: null list → all plugins,
empty list → disable). The wrapper's deepcopy-then-convert mirrors the kernel loop's
settings-copied-before-mutation rule.
**Probe:** `python/tests/unit/connectors/ai/test_service_utils.py` (wrapper + projection neighbors); .NET tests read-only this pass (dotnet CLI broken, standing block): `dotnet/src/SemanticKernel.Abstractions.Tests` `FunctionChoiceBehaviorTests` — selection assertions mirror the GetFunctions ladder above. Python side cross-probe: `python/tests/unit/agents/azure_ai_agent/test_agent_thread_actions.py::test_get_tools_with_fcb_disable_kernel_functions` (464 — full list still validated when advertisement disabled).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "prepare_settings_for_function_calling FunctionChoiceBehavior GetFunctions autoInvoke KernelException", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the deepcopy→convert→configure-only-if-present wrapper as the universal pre-request hook,
and the fail-early "never advertise what you cannot invoke" selection contract in both languages.
Adapt the selection input (dict filters vs function instances) to your host's registration model.
Omit the .NET JSON-polymorphic serialization of behaviors unless your host persists settings.
Coverage caveat: .NET connector-side invocation LOOP (AutoInvokeKernelFunctions budget semantics)
remains uncited — carried as the top next-pass target.
