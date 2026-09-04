<!-- capsule-v2 -->
# Streaming partial validation — allow_partial ladder and the final partial_output=False call

**Source:** pydantic-ai ( MIT) `main@b33cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a porter streams structured output, how does the framework validate incrementally (allow_partial) and then once more at the end, and why must the final validation be a distinct `partial_output=False` call even when content matches?

## AgentStream.stream_output partial→final validation
**Path/Symbol:** `pydantic_ai/result.py:AgentStream.stream_output` (74-101), `validate_response_output` (244-308), `_output.py:validate` (927-940).
**Signature:** `stream_output(*, debounce_by=0.1) -> AsyncIterator[OutputDataT]`; `validate_response_output(message, *, allow_partial=False)`.
****Data Shape:** `_cached_output` caches the final validated result; `_raw_stream_response.fternal_result_event` gates whether output validation runs at all.

### Decisive source
```python
async def stream_output(self, *, debounce_by=0.1):
    if self._cached_output is not None:
        yield deepcopy(self._cached_output); return
    last_response = None
    async for response in self.stream_response(debounce_by=debounce_by):
        if self._raw_stream_response.final_result_event is None or (
            last_response and response.parts == last_response.parts):
            continue
        last_response = response
        try:
            yield await self.validate_response_output(response, allow_partial=True)
        except (ValidationError, exceptions.ModelRetry):
            pass
    if self._raw_stream_response.final_result_event is not None:
        response = self.response
        self._cached_output = await self.validate_response_output(response)   # allow_partial=False
        yield deepcopy(self._cached_output)

# _output.py validate — the pydantic partial mode
pyd_allow_partial = 'trailing-strings' if allow_partial else 'off'
if isinstance(data, str):
    return self.validator.validate_json(data or '{}', allow_partial=pyd_allow_partial, context=validation_context)
else:
    return self.validator.validate_python(data or {}, allow_partial=pyd_allow_partial, context=validation_context)
```

**Flow:** `stream_output` iterates debounced `ModelResponse` snapshots; for each new one (skipping unchanged parts), it validates with `allow_partial=True` and yields the result, swallowing `ValidationError`/`ModelRetry` (partial data may not yet validate). After the stream, it runs ONE final validation with `allow_partial=False`, caches it, and yields it. The partial mode maps to pydantic's `allow_partial='trailing-strings'` (vs `'off'` for final).
**Invariant:** Output validators/functions are called multiple times with `ctx.partial_output=True` during streaming, then EXACTLY ONCE with `partial_output=False` at the end — even if the final content equals the last partial yield. This matters because validators may branch on `partial_output`, and users rely on the last yielded item being the fully validated output.
**Probe:** `tests/test_streaming.py:test_stream_output_partial_then_final_validation` (2367) — asserts the call log is `[(Foo(a=21,b='f'), True), (Foo(a=21,b='foo'), True), (Foo(a=21,b='foo'), False)]` with exactly one `False`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "stream_output allow_partial validate_response_output partial_output", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the partial-then-final validation ladder and the exactly-one-`partial_output=False` invariant; adapt the pydantic `allow_partial` mode string to your validator; omit nothing — the final distinct validation call is the portable invariant. Coverage clean.
