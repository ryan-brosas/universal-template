<!-- capsule-v2 -->
# Token-usage fallback ladder — how do you record token usage when `llm_output` is None or empty (LiteLLM/watsonx/streaming)?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Where does an async callback handler get total tokens when the provider response carries no `token_usage` block?

## TokenUsageTracker.on_llm_end
**Path/Symbol:** `src/cuga/backend/cuga_graph/utils/agent_loop.py:44-64` (`TokenUsageTracker`, `AsyncCallbackHandler`).
**Signature:** `async def on_llm_end(self, response: LLMResult, **kwargs)`.
**Data Shape:** input `LLMResult` with `generations: List[List[...]]` and optional `llm_output: dict`; output = two ActivityTracker collects (`collect_prompt(role="assistant", value=first.text)`, `collect_tokens_usage(total_tokens)`).

### Decisive source
```python
# generations can be empty on malformed provider responses — the same
# silent-loss class as the llm_output guard below.
generations = response.generations or []
first = generations[0][0] if generations and generations[0] else None
...
# llm_output is None (or lacks token_usage) for LiteLLM/watsonx/streaming
# responses; fall back to the message's usage_metadata before giving up.
token_usage = (response.llm_output or {}).get("token_usage") or {}
total_tokens = token_usage.get("total_tokens")
if total_tokens is None and first is not None:
    usage_metadata = getattr(getattr(first, "message", None), "usage_metadata", None)
    if usage_metadata:
        total_tokens = usage_metadata.get("total_tokens")
```

**Flow:** guard empty generations → take first generation's text as the assistant prompt record → try `llm_output.token_usage.total_tokens` → fall back to `generation.message.usage_metadata.total_tokens` → only collect when truthy (no zero-spam).
**Invariant:** every degenerate shape must be a NO-OP, never a crash — empty generations, `llm_output=None`, missing key, missing metadata all skip collection; the assistant-text collect happens independently of the token count.
**Probe:** `tests/unit/test_token_usage_tracker_guard.py` pins all six shapes: legacy path (:32), None llm_output (:42), llm_output-without-key (:54), no-op everywhere (:66), empty-generations WITH usage still counts tokens but skips prompt (:76), empty without usage is full no-op (:87).

## on_llm_start system/human split
**Path/Symbol:** `src/cuga/backend/cuga_graph/utils/agent_loop.py:66-129` (`split_system_human`, `on_llm_start`).
**Data Shape:** splits the raw prompt string on `"System: "` / `"\nHuman: "` markers into `(system_part, human_part)`; handles either-marker-only cases; unparsed prompts land wholly in the `system` bucket.
**Invariant:** tracking is best-effort string surgery — a prompt that doesn't contain both markers still gets recorded exactly once.
**Probe:** none directly (exercised via tracker integration); deterministic check: marker positions compared before slicing (`system_pos < human_pos`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "TokenUsageTracker on_llm_end usage_metadata fallback", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-source ladder (llm_output first, per-message usage_metadata second) plus the never-crash guards verbatim — any port to another LangChain-based agent inherits the same LiteLLM/streaming gap; adapt where your tracker records prompts/tokens; omit the System/Human string split if your callbacks receive structured messages instead of formatted strings. Direct tests pin all degenerate shapes.
