<!-- capsule-v2 -->
# .NET filter-onion mirror — DI-registered recursive onion, same ordering invariant, pre-seeded result context

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How does the .NET function-invocation filter chain differ from the Python index-0-insertion onion, and which ordering invariants do both planes share?

## Kernel filter registration and recursive dispatch
**Path/Symbol:** `dotnet/src/SemanticKernel.Abstractions/Kernel.cs:Kernel.AddFilters` (lines 282–307), `OnFunctionInvocationAsync` (309–326), `InvokeFilterOrFunctionAsync` (335–350).
**Signature:** `private static async Task InvokeFilterOrFunctionAsync(NonNullCollection<IFunctionInvocationFilter>? functionFilters, Func<FunctionInvocationContext, Task> functionCallback, FunctionInvocationContext context, int index = 0)`.
**Data Shape:** Three parallel filter families (function invocation, prompt render, auto function invocation) are each captured from DI ONCE at kernel construction; public properties lazily materialize an empty list via `Interlocked.CompareExchange` (132–151) and remain mutable after construction.

### Decisive source
```csharp
private void AddFilters()
{
    IEnumerable<IFunctionInvocationFilter> functionInvocationFilters = this.Services.GetServices<IFunctionInvocationFilter>();
    if (IsNotEmpty(functionInvocationFilters)) { this._functionInvocationFilters = new(functionInvocationFilters); }
    // ... prompt render + auto function invocation families, same shape ...
}

internal async Task<FunctionInvocationContext> OnFunctionInvocationAsync(
    KernelFunction function, KernelArguments arguments, FunctionResult functionResult,
    bool isStreaming, Func<FunctionInvocationContext, Task> functionCallback, CancellationToken cancellationToken)
{
    FunctionInvocationContext context = new(this, function, arguments, functionResult)
    { CancellationToken = cancellationToken, IsStreaming = isStreaming };
    await InvokeFilterOrFunctionAsync(this._functionInvocationFilters, functionCallback, context).ConfigureAwait(false);
    return context;
}

private static async Task InvokeFilterOrFunctionAsync(
    NonNullCollection<IFunctionInvocationFilter>? functionFilters,
    Func<FunctionInvocationContext, Task> functionCallback, FunctionInvocationContext context, int index = 0)
{
    if (functionFilters is { Count: > 0 } && index < functionFilters.Count)
    {
        await functionFilters[index].OnFunctionInvocationAsync(context,
            (context) => InvokeFilterOrFunctionAsync(functionFilters, functionCallback, context, index + 1)).ConfigureAwait(false);
    }
    else { await functionCallback(context).ConfigureAwait(false); }
}
```

**Flow:** At construction, `AddFilters()` pulls every registered `IFunctionInvocationFilter` (and the two sibling families) out of the DI container into a `NonNullCollection`. At invocation, a `FunctionInvocationContext` is built with the kernel, function, arguments, a PRE-SEEDED `FunctionResult`, plus `CancellationToken` and `IsStreaming`; the recursive forward-index onion then runs filter[i] with `next = () => InvokeFilterOrFunctionAsync(..., i + 1)` until the base case executes the function callback. First-registered filter is outermost: pre-`next` code runs in DI registration order, post-`next` code in reverse — the SAME invariant as Python's `(id, filter)` tuples inserted at index 0. Because the public list is live, filters can be inserted mid-pipeline AFTER construction (`kernel.FunctionInvocationFilters.Insert(1, ...)`) and the order follows the list position.
**Invariant:** Registration/list position fully determines onion depth — first registered runs first pre-`next` and last post-`next`; skipping `next` short-circuits the rest of the pipeline; exceptions propagate to the caller unless a filter catches them; the context's pre-seeded result means a filter can override the outcome without invoking the function at all.
**Probe:** `dotnet/src/SemanticKernel.UnitTests/Filters/FunctionInvocationFilterTests.cs::MultipleFiltersAreExecutedInOrderAsync` (129–185, exact six-entry executionOrder assertion), `InsertFilterInMiddleOfPipelineTriggersFiltersInCorrectOrderAsync` (979–1025), `FunctionFilterSkippingWorksCorrectlyAsync` (397), `FunctionFilterPropagatesExceptionToCallerAsync` (446); `KernelFilterTests.cs::FiltersAreClonedWhenRegisteredWithDI` (12). Caveat: tests were read directly, not executed — the dotnet CLI in this environment fails to load its apphost.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "InvokeFilterOrFunctionAsync OnFunctionInvocationAsync IFunctionInvocationFilter AddFilters", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the shared cross-language invariant — registration order = pre-`next` order, reversed = post-`next` order, skip-`next` short-circuits, uncaught exceptions propagate — as the contract any host's filter plane must satisfy. Adapt the registration mechanism to your host: .NET captures filters from DI at construction (with a live mutable list for late insertion) while Python inserts at index 0 of a per-kernel list on every add; both keep the same observable order. Omit the `Interlocked.CompareExchange` lazy-empty-list detail unless your host is multi-threaded over the filter collection; note the .NET-only pre-seeded `FunctionResult` in the context (Python builds the result inside the inner handler).
