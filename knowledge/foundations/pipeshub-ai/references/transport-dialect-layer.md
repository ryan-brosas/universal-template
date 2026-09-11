<!-- capsule-v2 -->
# Provider transport dialect layer — how does one LLMTransport map framework messages to each provider's wire format?

**Source:** pipeshub-ai (Apache-2.0) `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** A porter adding a new provider (or reusing one) must know the ONE choke point every LLM call passes through and the per-provider dialect rules (message/tool formatting, prompt-cache breakpoints, thinking/effort knobs, structured-output trick, error→retry classification) that keep the agent loop provider-agnostic.

## The LLMTransport ABC — the single choke point
**Path/Symbol:** `transport/base.py:LLMTransport` (33-131); `transport/base.py:RetryConfig` (15-30).
**Signature:** `async complete(messages, tools=None, system=None, model=None, thinking_budget=None, effort=None, system_blocks=None) -> ModelResponse`; `async complete_structured(messages, output_schema, system=None, model=None) -> StructuredResponse`; `stream(...) -> AsyncIterator[StreamEvent]`.
**Data Shape:** Every call returns its full outcome as an explicit value — `ModelResponse` (assembled `AssistantMessage` + `TokenUsage` + `StopReason` + model), `StructuredResponse` (data + usage + model), or a `StreamEvent` stream terminated by **exactly one** `StreamCompleteEvent`. No side-channel `last_usage` attribute. `thinking_budget`/`effort`/`system_blocks` are best-effort knobs: a transport that doesn't support one must silently ignore it (never raise). `system_blocks` is a stable/volatile split; Anthropic attaches `cache_control` to the stable block only.

### Decisive source
```python
# transport/base.py — the contract every transport honors
class LLMTransport(ABC):
    @property
    @abstractmethod
    def provider(self) -> str: ...
    @property
    def model_name(self) -> str:
        return getattr(self, "_model", "") or ""
    @abstractmethod
    async def complete(self, messages, tools=None, system=None, model=None,
                       thinking_budget=None, effort=None, system_blocks=None) -> ModelResponse: ...
    @abstractmethod
    async def complete_structured(self, messages, output_schema, system=None, model=None) -> StructuredResponse: ...
    @abstractmethod
    def stream(self, messages, tools=None, system=None, model=None,
               thinking_budget=None, effort=None, system_blocks=None) -> AsyncIterator[StreamEvent]: ...

class RetryConfig(BaseModel):
    max_retries: int = 3
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 60.0
    retryable_status_codes: list[int] = [429, 500, 502, 503, 504, 529]  # 529 = Anthropic overloaded_error
```

**Flow:** `Agent.step()`/planning/critique/`parse_intent`/`best_of_n`/auto-compact/`RubricGrader`/`SkillExtractor` all call `TransportRegistry.resolve(provider)` (directly or via `ModelSpec.resolve()`→`TransportModel`) to get a transport, then call `complete`/`complete_structured`/`stream`. The registry caches one instance per provider after first resolve; `LazyTransport` defers instantiation until first `complete_structured` use.
**Invariant:** The SDK is an implementation detail that never leaks past the interface — callers see only `LLMTransport`. A provider response without well-formed usage must record zero usage, never crash the loop. Every provider error is classified into `TransportError(status_code, retryable)` so the retry ladder (`retry.py`/`retry_with_status.py`) can back off on transients and re-raise immediately on non-retryables.

## Per-provider dialect rules (the part a porter gets wrong)
**Path/Symbol:** `transport/anthropic.py:AnthropicTransport` (43-434); `transport/openai.py:OpenAITransport` (40-352); `transport/ollama.py:OllamaTransport` (34-287).
**Signature:** `AnthropicTransport(api_key, model=DEFAULT_MODEL, max_tokens=20000)`; `OpenAITransport(api_key, model=DEFAULT_MODEL, base_url=None)`; `OllamaTransport(base_url="http://localhost:11434", model="llama3.2", timeout=120, num_ctx=None, temperature=0.2)`.

### Decisive source — three dialects, one interface
```python
# anthropic.py — tool_result role is "user" with a tool_result block; thinking blocks ignored
if msg.role == MessageRole.TOOL:
    block = {"type": "tool_result", "tool_use_id": msg.tool_call_id,
             "content": (msg.content or "") + getattr(msg, "step_footer", "")}
    if getattr(msg, "is_error", False): block["is_error"] = True
    return {"role": "user", "content": [block]}
# truncated = stop_reason == "max_tokens"  → surface so the loop recovers, never execute a partial tool call

# openai.py — tool role is "tool" with tool_call_id; assistant tool_calls carry json.dumps(arguments)
# ollama.py — tool message has NO tool_call_id round-trip (model disambiguates from content alone);
#   _options = {"temperature": t, "repeat_penalty": 1.0, "top_p": 1.0}  # repeat_penalty>1 corrupts tool JSON
```

**Flow (per-provider differences a porter must preserve):**
- **Anthropic:** `_apply_prompt_cache` marks ONE large tool result NOT in the final 2 messages (≥300 chars) as `cache_control: ephemeral`; `_apply_tool_cache` marks the last tool schema (copies, never mutates caller dicts); `_build_system_kwargs` caches only block[0] of the stable/volatile split. `thinking_budget` sets `thinking={type:enabled, budget_tokens}` AND grows `max_tokens = max(self._max_tokens, budget+1024)` (extended thinking requires max_tokens > budget). `complete_structured` uses the forced-tool trick: a `structured_output` tool + `tool_choice={type:tool,name:structured_output}`. `_RETRYABLE_STATUS_CODES={429,500,502,503,504,529}`.
- **OpenAI:** `_format_messages` prepends a `system` message; `_format_tools` uses `{type:function,function:{name,description,parameters}}`; `complete_structured` uses `tool_choice={type:function,function:{name:structured_output}}`; `effort` maps to `reasoning_effort`; streaming accumulates fragmented tool-call argument deltas by `tc_delta.index`; `_RETRYABLE_STATUS_CODES={429,500,502,503,504}` (no 529). `system_blocks` joined with `"\n\n"` when `system` absent.
- **Ollama:** raw httpx NDJSON to `/api/chat`; `complete_structured` uses native `format=output_schema` (constrained JSON), NOT a tool trick; streaming parses newline-delimited JSON, capturing the last `tool_calls` message and usage from the `done` chunk; `_wrap_error` treats `httpx.ConnectError`/`TimeoutException` and 429/5xx as retryable.

**Probe:** `tests/unit/agent_loop_lib/transport/test_anthropic_coverage.py` (pins `_apply_prompt_cache` marks last large tool result before final two messages; `thinking_budget` grows max_tokens; `max_tokens` stop sets `truncated`; forced-tool structured output; 529/500 retryable vs 400 not). `test_openai_coverage.py`, `test_ollama_coverage.py` (pins `repeat_penalty=1.0`, `format=` structured output, tool-call streaming accumulation, tool message has no id).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "AnthropicTransport complete", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "LLMTransport", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the `LLMTransport` ABC as the single choke point, the explicit-value return contract (no `last_usage`), the defensive usage coercion to zero, and the `TransportError(status_code, retryable)` classification with 529 included for Anthropic. Adopt per-provider dialect rules: Anthropic cache-breakpoint discipline (one message + one tool + stable system block ≤ 4 breakpoints), thinking-budget max_tokens growth, OpenAI `reasoning_effort` + index-keyed tool-call accumulation, Ollama `repeat_penalty=1.0` + native `format=` structured output. Adapt thresholds (20k max_tokens, 300-char cache min, 120s timeout) and model defaults to host. Omit provider-specific SDK internals (SSE parsing, thinking-block handling) — they're the SDK's job, not portable. Direct tests confirm all invariants; index coverage `no_recorded_issue`+`metadata_match` (best-effort caveat).
