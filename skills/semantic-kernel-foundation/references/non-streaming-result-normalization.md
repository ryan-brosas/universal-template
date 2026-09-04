<!-- capsule-v2 -->
# Non-streaming result normalization — generators collapse into one list; FunctionResult passes through with used-argument provenance

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** In the NON-streaming path, what is a tool's sync/async/generator return normalized into, and how does the result record which arguments produced it?

## `_invoke_internal` await/consume ladder
**Path/Symbol:** `python/semantic_kernel/functions/kernel_function_from_method.py:KernelFunctionFromMethod._invoke_internal` (lines 97–116); stream wiring decided in `__init__` (83–93).
**Signature:** `async def _invoke_internal(self, context: FunctionInvocationContext) -> None`.
**Data Shape:** `context.result` ends as a single `FunctionResult`. Its `value` is the awaited coroutine result, or ONE LIST for generator tools. If the tool returned its own `FunctionResult`, it is kept untouched. Metadata records `"arguments"` and `"used_arguments"`.

### Decisive source
```python
function_arguments = self.gather_function_parameters(context)
result = self.method(**function_arguments)
if isasyncgen(result):
    result = [x async for x in result]
elif isawaitable(result):
    result = await result
elif isgenerator(result):
    result = list(result)
if not isinstance(result, FunctionResult):
    result = FunctionResult(
        function=self.metadata, value=result,
        metadata={"arguments": context.arguments, "used_arguments": function_arguments},
    )
context.result = result
```

**Flow:** Gather kwargs → call synchronously (works for both `def` and `async def` because coroutines are awaitables) → normalize: async generator consumed fully via `async for` into a list; awaitable awaited; sync generator materialized via `list()` → wrap into FunctionResult unless the tool already produced one → assign to context so filters/telemetry see it.
**Invariant:** Non-streaming invocation NEVER yields partials: streaming output collapses to a complete list as the value. The stream path is chosen at construction (`stream_method` auto-set when the method is an async/sync generator; otherwise None ⇒ `_invoke_internal_stream` raises NotImplementedError).
**Probe:** `python/tests/unit/functions/test_kernel_function_from_method.py::test_invoke_gen` / `::test_invoke_gen_async` (195–220) pin `result.value == [""]` for both generator kinds AND that `invoke_stream` works for them; `::test_invoke_non_async` / `::test_invoke_async` (165–192) pin plain returns plus the NotImplementedError when streaming a non-generator.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "_invoke_internal isasyncgen isawaitable used_arguments", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-way normalization ladder (async-gen → list, awaitable → await, gen → list, else value) for any runner whose non-streaming API must stay total over tool kinds. Adapt where provenance lives: keeping `arguments` + `used_arguments` in result metadata is what lets filters explain/replay a call. Omit FunctionResult passthrough only if your tools can never return richer result objects.
