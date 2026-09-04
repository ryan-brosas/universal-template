<!-- capsule-v2 -->
# Adapter escape-hatch kwargs — how do user-supplied extra_query/extra_body/extra_args reach the provider without leaking or double-sending?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** When a model adapter exposes typed settings PLUS raw escape hatches (`extra_query`, `metadata`, `extra_body`, `extra_args`), what merge order keeps explicit caller kwargs authoritative, how is a key promoted from an escape hatch to a top-level parameter without being sent twice, and which settings must NOT leak into the request when their precondition (e.g. tools present) is absent?

## Fixed-precedence merge + reasoning_effort promotion + precondition gating
**Path/Symbol:** `src/agents/extensions/models/litellm_model.py:` `_get_reasoning_effort` (:172–209), chat-path extra-kwargs build (:616–640) with `parallel_tool_calls` gating (:584) and the `acompletion` call (:655–672); `src/agents/extensions/models/any_llm_model.py:` reasoning fallback (:914–920), `_build_chat_extra_kwargs` (:1364–1374), `_build_responses_extra_kwargs` (:1376–1385).
**Signature:** `_get_reasoning_effort(model_settings) -> Any | None`; `_build_chat_extra_kwargs(model_settings) -> dict[str, Any]`.
**Data Shape:** input = `ModelSettings(extra_query: dict | None, metadata: dict | None, extra_body: dict | None, extra_args: dict[str, Any] | None, reasoning: Reasoning | None, parallel_tool_calls: bool | None)`; output = the kwargs dict splatted into the provider call; every value is a COPY — the caller's settings objects are never mutated.

### Decisive source
```python
# litellm chat path: fixed merge order, copies at every boundary
extra_kwargs: dict[str, Any] = {}
if model_settings.extra_query:
    extra_kwargs["extra_query"] = copy(model_settings.extra_query)
if model_settings.metadata:
    extra_kwargs["metadata"] = copy(model_settings.metadata)
if model_settings.extra_body is not None:
    extra_body = copy(model_settings.extra_body)
    if isinstance(extra_body, dict) and reasoning_effort is not None:
        extra_body.pop("reasoning_effort", None)      # promoted → remove from origin
        if not extra_body:
            extra_body = None
    if extra_body is not None:
        extra_kwargs["extra_body"] = extra_body
if model_settings.extra_args:
    extra_kwargs.update(model_settings.extra_args)    # explicit caller kwargs win LAST
...
parallel_tool_calls = model_settings.parallel_tool_calls if converted_tools else None
```

**Flow:** both adapters build the chat-path kwargs in the same fixed precedence: `extra_query` (copied) → `metadata` (copied) → `extra_body` (copied) → `extra_args` LAST via dict update, so explicit caller kwargs override everything. The litellm adapter adds a promotion ladder for `reasoning_effort`: `model_settings.reasoning.effort` (checked with `is not None`, so even a falsy `Reasoning` object promotes) > `extra_body["reasoning_effort"]` > `extra_args["reasoning_effort"]`; when a value is promoted from an escape hatch, the key is popped from the COPIED `extra_body` (and `extra_body` set to `None` if now empty) so it is sent exactly once, at top level; `Reasoning.summary` is dropped with a warning on the LiteLLM chat path because that surface only accepts a scalar effort. The any-llm adapter uses the shorter ladder (`reasoning.effort` > `extra_args` only). Precondition gating: `parallel_tool_calls` is forwarded only when `converted_tools` is non-empty (else `None`), so a setting with no tools never leaks into the request; litellm additionally sets `_skip_mcp_handler=True` when SDK tools were converted (LiteLLM's proxy-only MCP discovery would add unsupported server dependencies) and disables provider-managed retries when the runner owns retrying.
**Invariant:** escape hatches are merged in a fixed precedence (typed settings < extra_body < extra_args) with a copy at every boundary (caller settings are never mutated — tests assert the original dicts are intact after the call), promoted keys are removed from their origin so nothing is sent twice, and settings whose precondition is absent are omitted rather than sent as false/default.
**Probe:** `tests/models/test_litellm_extra_body.py::test_falsy_reasoning_effort_is_preserved` (:14 — falsy `Reasoning` still promotes `"low"`), `::test_extra_body_reasoning_effort_is_promoted` (:103 — `captured["reasoning_effort"] == "none"` AND `captured["extra_body"] == {"cached_content": "some_cache"}` AND original settings untouched), `::test_reasoning_effort_prefers_model_settings` (:140), `::test_extra_body_reasoning_effort_overrides_extra_args` (:180), `tests/models/test_kwargs_functionality.py::test_litellm_kwargs_forwarded` (:26 — custom_param/seed/stop/logit_bias all reach `acompletion`), `::test_litellm_only_forwards_parallel_tool_calls_with_converted_tools` (:77 — `parallel_tool_calls is None` when no tools), `::test_empty_kwargs_handling` (:277), `::test_reasoning_effort_falls_back_to_extra_args` (:330).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", file_pattern: "litellm_model.py", query: "extra body extra args reasoning effort promotion", limit: 20 });
await mcp.codebase_memory.get_code_snippet({ project: "openai-agents-python", qualified_name: "openai-agents-python.src.agents.extensions.models.litellm_model.LitellmModel._get_reasoning_effort" });
```

## Verdict
Adopt the fixed-precedence escape-hatch merge (typed < extra_body < extra_args-last-wins) with copies at every boundary, promote-and-pop for keys that have a first-class top-level slot, and precondition gating (omit rather than default) for any multi-provider adapter that exposes raw kwargs. Adapt the promotion ladder per provider surface and the MCP-handler skip if your backend has no proxy discovery. Omit the retry-disable interplay if your runner does not own retries. Coverage: direct source+test reading fallback this pass (Codebase Memory MCP not connected); decisive ranges read from checkout at fe45b415.
