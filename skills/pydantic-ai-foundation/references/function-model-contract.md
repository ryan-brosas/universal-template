<!-- capsule-v2 -->
# FunctionModel / AgentInfo — how does a framework let tests script the model without a network?

**Source:** pydantic-ai MIT `main@fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** What's the minimal contract for a user-supplied function to stand in for an LLM, and what does it need to know about the agent?

## FunctionModel test-double contract
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/models/function.py:FunctionModel` (:52-247), `AgentInfo` (:250-272), `DeltaToolCall/DeltaThinkingPart` (:275-303), `_estimate_usage` (:419-477).
**Signature:** `FunctionDef = Callable[[list[ModelMessage], AgentInfo], ModelResponse | Awaitable[ModelResponse]]`; `StreamFunctionDef = Callable[..., AsyncIterator[str | DeltaToolCalls | DeltaThinkingCalls | BuiltinToolCallsReturns]]`; `DeltaToolCall(name=None, json_args=None, *, tool_call_id=None)`.
**Data Shape:** `AgentInfo(function_tools, allow_text_output, output_tools, model_settings, model_request_parameters, instructions)` — frozen snapshot of what the agent declared for THIS request; the fake model reads it instead of probing the agent.

### Decisive source
```python
# function.py:61-62 — a test double claims EVERY channel: its profile is the whole simulation
# A test double has no wire, so its "renderer" is whatever the test simulates: declaring every
# mode makes the `profile=` handed to it the whole simulation (no claim still means no channel),
# instead of requiring a subclass to restate what the profile already says.
supported_tool_deferral_modes = frozenset({'standalone', 'with_tool_search'})
supported_tool_addition_modes = frozenset({'by_reference', 'with_definitions'})

# function.py:166-174 — async/sync callables dispatched by shape; await_maybe converges both arms
result: ModelResponse | Awaitable[ModelResponse]
if _utils.is_async_callable(self.function):
    result = self.function(messages, agent_info)
else:
    result = await _utils.run_in_executor(self.function, messages, agent_info)
response = await _utils.await_maybe(result)
assert isinstance(response, ModelResponse), response
response.model_name = self._model_name
if not response.usage.has_values():  # pragma: no branch
    response.usage = _estimate_usage(chain(messages, [response]), ...)
```
(Pre-855f441 this was an `inspect.iscoroutinefunction` branch; the current shape-dispatch plus executor-routing details are owned by `function-model-callable-instances.md`.)

**Flow:** Agent resolves the model → `FunctionModel.request()` builds `AgentInfo` from `ModelRequestParameters` (plus extracted instructions) → user callable inspects full history + info, returns a hand-built `ModelResponse` (or awaits one; sync callables run in an executor and MAY return coroutines — see `function-model-callable-instances.md`) → if the response carries no usage, a rough token estimate (~50 overhead + whitespace/punct-split word counts over the whole exchange) fills it so downstream usage assertions see plausible numbers → streaming variant wraps whatever the stream callable RETURNS in `PeekableAsyncStream` and REQUIRES a non-empty first item (`ValueError` otherwise); delta dicts map index→`DeltaToolCall{name?, json_args?}` fragments through the standard parts manager.
**Invariant:** (1) Stream functions must yield ONE kind per stream (all text OR all DeltaToolCalls OR all DeltaThinkingCalls OR all builtin parts) — mixing is undefined (:313-319). (2) The deferral/addition mode claim lives on the MODEL class (test doubles claim all modes), keeping profile-driven behavior testable without subclasses. (3) Estimated usage marks nothing special — tests that assert exact usage must supply their own.
**Probe:** `tests/models/test_model_function.py::test_sync_function_returning_coroutine` (:142), `::test_stream_text` (:651); `tests/models/test_model_test.py::test_delta_part_without_native_profile_still_raises` (:146).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "FunctionModel AgentInfo DeltaToolCall estimate_usage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-function test-double pattern (sync/async single-shot + delta-stream) and the AgentInfo snapshot as the seam between agent and fake model; adapt the delta shapes to your stream protocol; omit token estimation heuristics if your tests assert usage explicitly. Caveat: source re-verified at pin `fde1bbb6` 2026-08-24 (callable-instance routing split out to its own capsule).
