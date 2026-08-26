<!-- capsule-v2 -->
# Inner-handler error absorption — crashing tools feed the model an error string, and results are snapshotted

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** When a plugin tool raises during model-driven auto-invocation, should the exception reach the host caller, and how do you stop later filter mutations from corrupting what was already written to chat history?

## Kernel._inner_auto_function_invoke_handler + result deepcopy
**Path/Symbol:** `python/semantic_kernel/kernel.py:Kernel._inner_auto_function_invoke_handler` (lines 465–484) with the snapshot in `invoke_function_call` (lines 450–452).
**Signature:** `async def _inner_auto_function_invoke_handler(self, context: AutoFunctionInvocationContext) -> None`.
**Data Shape:** `context.function_result: FunctionResult` is pre-seeded with `value=None`; on failure its value becomes a plain error string; on success it holds the tool's return. Post-stack, `invoke_function_call` deep-copies `.value` before building the `FunctionResultContent`.

### Decisive source
```python
try:
    result = await context.function.invoke(context.kernel, context.arguments,
        metadata=context.function_call_content.metadata | context.function_call_content.to_dict() ...)
    if result:
        context.function_result = result
except Exception as exc:
    logger.exception(...)
    value = f"An error occurred while invoking the function {context.function.fully_qualified_name}: {exc}"
    if context.function_result is not None:
        context.function_result.value = value
    else:
        context.function_result = FunctionResult(function=context.function.metadata, value=value)
    return
...
# Snapshot the tool's return value so later mutations don't leak back
if invocation_context.function_result and invocation_context.function_result.value is not None:
    invocation_context.function_result.value = deepcopy(invocation_context.function_result.value)
```

**Flow:** The handler sits at the center of the auto-function-invocation filter onion. A raising tool is caught, logged, and converted into a descriptive error string placed into `FunctionResult.value`; the filter stack then unwinds normally, so auto-invoke filters observe errors as ordinary values they may rewrite. After the stack returns, the wrapper deepcopies the value so any post-return mutation of mutable results cannot retroactively change the message appended to history. Return contract: the caller receives the context only if `terminate` was set, else `None` (line 463).
**Invariant:** Tool exceptions never propagate to the auto-invoke loop or the LLM round-trip; history messages are immutable after being written.
**Probe:** `python/tests/unit/kernel/test_kernel.py::test_invoke_function_call_throws_during_invoke` (409–437) drives a failing invoke through the full path and asserts completion without exception.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "_inner_auto_function_invoke_handler FunctionResult error", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt error-as-value absorption at the innermost layer plus the post-filter deepcopy snapshot — together they give filters full authority over error presentation while keeping history write-once. Adapt the error string template to include retry hints your models respond to. Omit the `metadata | to_dict()` merge if you have no per-call-content metadata channel.
