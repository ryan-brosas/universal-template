<!-- capsule-v2 -->
# Context summarizer trigger/execution split — how do you trigger summarization on TOTAL context (messages+tools+prompt) while the middleware only counts messages?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How does ContextSummarizer decide WHEN to summarize vs HOW it executes the summarize, and why is the LangChain middleware handed a `(tokens, 1)` trigger?

## ContextSummarizer wrapper over SummarizationMiddleware
**Path/Symbol:** `src/cuga/backend/cuga_graph/utils/context_summarizer.py:36-191` (`ContextSummarizer.__init__`, `_build_middleware_kwargs`, `should_summarize`, `_check_trigger_conditions`).
**Signature:** `should_summarize(self, messages: List[BaseMessage], tools=None, system_prompt=None) -> Tuple[bool, Dict[str, Any]]`; `summarize_messages(self, messages) -> Tuple[List[BaseMessage], Dict]`.
**Data Shape:** Config from `settings.context_summarization` (`trigger_fraction`, `trigger_tokens`, `trigger_messages`, `keep_last_n_messages`, `trim_tokens_to_summarize`, `custom_summary_prompt`). Returns `(bool, metrics)` where metrics carry BOTH `token_count` (messages only, display) and `total_token_count` (messages+tools+system prompt, triggering).

### Decisive source
```python
# context_summarizer.py:133-141
# IMPORTANT: We do our own trigger checking in should_summarize() which includes
# tools, system prompt, and overhead. The middleware only counts message tokens.
# So we pass a very low trigger (1 token) to ensure the middleware always summarizes
# when we call it (after our trigger check passes).
middleware_trigger = ("tokens", 1)
kwargs = {"model": self.model, "trigger": middleware_trigger, "keep": keep_config,
          "token_counter": self.token_counter.token_counter, ...}
```
Trigger check runs on total usage: `_calculate_metrics` computes `usage_percentage = total_token_count / context_size * 100` (:218), and `_check_trigger_conditions` compares fraction/tokens/messages-count in order, first hit wins with a human-readable `trigger_reason` (:230-265). Message-count trigger counts only messages AFTER the last summary via `_count_messages_since_last_summary` (:267-284), preventing immediate re-trigger.

**Flow:** call site (`AgentState._summarize_message_list`, agent_state.py:1164-1237): `should_summarize()` → if triggered → `summarize_messages()` → middleware invoked manually via internal APIs (`LangChainAgentState(messages=...)` + `Runtime()`, then `abefore_model(state, runtime)`) → result dict filtered of `RemoveMessage` → metrics stored under `self.last_summarization_metrics[list_name]` only for `chat_messages` (`store_metrics=True` only on that list).
**Invariant:** The middleware must NEVER decide its own trigger (its token count ignores tools+system prompt, which dominate real context); the 1-token trigger makes it a pure executor. A porter who passes the configured trigger to the middleware gets summarization that fires far too late on tool-heavy agents.

**Probe:** `tests/unit/test_context_summarizer.py::test_should_summarize_fraction_trigger / test_should_summarize_token_trigger / test_summarize_model_invocation` — pins per-trigger firing and the manual middleware invocation (20+ tests in the file cover init, triggers, metrics).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "ContextSummarizer should_summarize middleware trigger", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-layer split (own total-context trigger check + executor-only middleware at `(tokens, 1)`) and the since-last-summary message counter. Adapt the metric dict keys to your tracker. Omit the LangChain version pin dance (see hard-truncation capsule). Direct tests exist and are indexed.
