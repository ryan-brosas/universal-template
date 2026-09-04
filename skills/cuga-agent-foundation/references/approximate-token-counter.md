<!-- capsule-v2 -->
# Approximate token counter — how do you count context tokens proactively (before the call) with graceful degradation and per-vendor tuning?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How does the proactive counter handle unknown message types, tool-schema overhead, and vendor-specific tokenizer ratios without a real tokenizer?

## TokenCounter over count_tokens_approximately
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/../utils/token_counter.py:466-744` (`TokenCounter.__init__`, `count_message_tokens`, `count_tool_tokens`, `count_total_context_tokens`, `calculate_usage_percentage`), fallback constant `CHARS_PER_TOKEN_FALLBACK = 4` (:18).
**Signature:** `count_message_tokens(messages: List[BaseMessage]) -> int`; `count_tool_tokens(tools) -> int`; `count_total_context_tokens(messages, tools=None, system_prompt=None) -> int`.
**Data Shape:** constructor picks a counter partial: `chars_per_token=3.3` when `model._llm_type == "anthropic-chat"` OR model_name contains `"claude"`, else LangChain's `count_tokens_approximately` default.

### Decisive source
```python
try:
    converted_messages = [convert_to_proper_message_type(msg) for msg in messages]
    return self.token_counter(converted_messages)
except ValueError as e:
    if "Unknown BaseMessage type" in str(e):
        logger.warning(...)          # conversion gap — degrade, don't crash
    ...
    total_chars = sum(len(str(msg.content)) for msg in messages)
    return total_chars // CHARS_PER_TOKEN_FALLBACK
```
And the total-context composition (:616-623):
```python
message_tokens = self.count_message_tokens(messages)
tool_tokens = self.count_tool_tokens(tools) if tools else 0
prompt_tokens = self.estimate_tokens(system_prompt) if system_prompt else 0
overhead = int(message_tokens * 0.15)   # message formatting, special tokens, etc.
total = message_tokens + tool_tokens + prompt_tokens + overhead
```

**Flow:** convert generic BaseMessage instances to concrete types → approximate count → on ANY failure fall back to `chars // 4` → tools counted separately (name+description text + serialized args_schema; per-tool exception ⇒ assume **200 tokens**) → sum with 15% overhead. This total is what the summarizer's `(tokens, 1)` trigger consumes.
**Invariant:** counting NEVER raises — every failure mode degrades to a rougher estimate; tool overhead must be included because the LangChain middleware's own count ignores it (the reason ContextSummarizer owns its own check); Anthropic-family prompts need 3.3 chars/token or triggers fire ~15% late.
**Probe:** no direct unit test for TokenCounter itself (coverage caveat); deterministic checks: empty list → 0; malformed message list still returns an int ≥ chars/4; per-tool failure adds exactly 200. The consumer (`context_summarizer.py`) is covered by `src/cuga/sdk_core/tests/test_context_summarization_sdk.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "TokenCounter count_total_context_tokens count_tokens_approximately", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the never-raise degradation ladder (typed-convert → approx-count → chars/4) and the three-component total (messages+tools+prompt+15%) whenever you gate summarization on token counts; adapt the chars-per-token ratios and the 200-token/tool assumption to your fleet; omit tool counting only if your middleware already includes schemas in its own count (then keep the wrapper anyway — see context-summarization-triggers). Coverage caveat: no direct test file; behavior verified by whole-source read + consumer tests.
