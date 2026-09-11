<!-- capsule-v2 -->
# Streaming exception smuggling — the `exception` metadata key on yielded FunctionResults

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How does an error raised inside a streaming function travel to a caller that is already consuming a stream, without breaking the async-generator protocol?

## METADATA_EXCEPTION_KEY consumer contract
**Path/Symbol:** `python/semantic_kernel/const.py:5` (key definition) and `python/semantic_kernel/kernel.py:Kernel.invoke_stream` (lines 143–153) / `Kernel.invoke_prompt_stream` (lines 302–312).
**Signature:** `METADATA_EXCEPTION_KEY: Final[str] = "exception"`; consumers check `stream_message.metadata.get(METADATA_EXCEPTION_KEY, None)` on every yielded item of `function.invoke_stream(...)`.
**Data Shape:** Stream items are either partial content (`StreamingContentMixin`) or a sentinel `FunctionResult` whose `metadata["exception"]` holds an `Exception`.

### Decisive source
```python
async for stream_message in function.invoke_stream(self, arguments):
    if isinstance(stream_message, FunctionResult) and (
        exception := stream_message.metadata.get(METADATA_EXCEPTION_KEY, None)
    ):
        raise KernelInvokeException(
            f"Error occurred while invoking function: '{function.fully_qualified_name}'"
        ) from exception
    function_result.append(stream_message)
    yield stream_message
```

**Flow:** An inner streaming implementation that fails wraps the failure in a final `FunctionResult(value=..., metadata={"exception": exc})` instead of raising mid-generator; the kernel-level wrapper inspects each item, converts any flagged result into a chained `KernelInvokeException`, and otherwise forwards partials untouched.
**Invariant:** Partials already yielded stay valid; the exception surfaces exactly once, chained, at the point the sentinel arrives — never as an unstructured generator crash.
**Probe:** `python/tests/unit/kernel/test_kernel.py::test_invoke_stream_functions_throws_exception` (lines 184–199) injects a `FunctionResult(metadata={METADATA_EXCEPTION_KEY: ...})` and asserts the key survives the yield boundary. **Coverage caveat:** at pin `b39d95a3` no library-internal producer exists — grep shows only `const.py`, the two kernel consumers, and test fixtures; custom `KernelFunction._invoke_internal_stream` implementers are expected to set it. Cite this capsule as a consumer-side contract, not a producer path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "METADATA_EXCEPTION_KEY invoke_stream exception", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sentinel-metadata pattern whenever your host streams from generators that cannot raise cleanly (async generators that raise lose buffered output). Adapt the key name and payload type (exception object vs serialized message) to your error channel. Omit for hosts where you control both ends and can simply let the generator raise — but then document that already-yielded chunks are orphaned.
