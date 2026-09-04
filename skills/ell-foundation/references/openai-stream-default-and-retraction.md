<!-- capsule-v2 -->
# openai stream default and retraction — why does ell stream by default and when does it silently stop?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** How do I default to streaming for UX while keeping tool calls, structured output, and usage accounting intact?

## inject-then-retract streaming
**Path/Symbol:** `src/ell/providers/openai.py:OpenAIProvider.translate_to_provider` (:29-91) + `translate_from_provider` (:93-163).
**Signature:** `translate_to_provider(self, ell_call: EllCallParams) -> Dict[str, Any]`.
**Data Shape:** default injection `{"stream": True, "stream_options": {"include_usage": True}}`; retraction pops both keys; endpoint flips to `client.beta.chat.completions.parse` when `response_format` is a BaseModel subclass.

### Decisive source
```python
# openai.py:30-39
final_call_params = ell_call.api_params.copy()
final_call_params["model"] = ell_call.model
# Stream by default for verbose logging.
final_call_params["stream"] = True
final_call_params["stream_options"] = {"include_usage": True}

if ell_call.tools or final_call_params.get("response_format") or (regisered_model := config.registry.get(ell_call.model, None)) and regisered_model.supports_streaming is False:
    final_call_params.pop("stream", None)
    final_call_params.pop("stream_options", None)
```

**Flow:** tools, response_format, or a registered model with `supports_streaming=False` retract streaming (tool-call deltas unsupported upstream at this pin). In the streamed response path, chunks accumulate per choice index into `defaultdict(list)`, text is re-joined per index, and each joined message is wrapped `_lstr(content=text, origin_trace=origin_id)`; chunk metadata (minus choices) updates the metadata dict so usage from the final chunk survives. Refusals on non-streamed parsed responses raise ValueError with the refusal text.
**Invariant:** streaming is a presentation/latency optimization that must never change message semantics — reassembly produces exactly one Message per choice index, identical in shape to the non-streaming branch. The walrus-operator registry probe tolerates unregistered models (`registry.get(..., None)`), so unknown model names keep streaming.
**Probe:** `tests/test_openai_provider.py:test_translate_to_provider_streaming_enabled` (:86-98) pins injected keys; `test_translate_to_provider_streaming_disabled_due_to_response_format` (:122-133) pins retraction (both keys absent); `test_translate_from_provider_with_usage_metadata` (:398-436) pins usage extraction through the stream path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "stream chunks index", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: ext-ell.tests.test_openai_provider.TestOpenAIProvider.test_translate_from_provider_with_multiple_chunks @ tests/test_openai_provider.py:437-464
```

## Verdict
Adopt inject-then-retract as the pattern for optional streaming behind one code path. Adapt the retraction trigger list to whichever features your vendor cannot stream. Omit `supports_streaming` plumbing if your registry has no such flag — but keep it data-driven (a registry field), not hardcoded model lists.
