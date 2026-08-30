<!-- capsule-v2 -->
# Temp-state summarization wrapper — how do you summarize messages for nodes OUTSIDE the graph without touching checkpointed state?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How can a non-graph caller (reflection prompts, chat agents) reuse the exact state-backed summarization pipeline, and why must the model NOT be wrapped with `with_config(callbacks=...)` first?

## apply_context_summarization via throwaway AgentState
**Path/Symbol:** `src/cuga/backend/cuga_graph/utils/context_management_utils.py:68-148` (`apply_context_summarization`).
**Signature:** `async def apply_context_summarization(messages: List[BaseMessage], model: Any, *, system_prompt=None, tools=None, tracker=None, variables_storage=None, variable_counter_state=None, variable_creation_order=None, message_list_name="chat_messages") -> List[BaseMessage]`.
**Data Shape:** Builds `AgentState(**{"input": "", "url": "", message_list_name: list(messages), ...optional variable passthroughs})`; returns the summarized list from that attribute, or the ORIGINAL list on any error (never raises).

### Decisive source
```python
# context_management_utils.py:106-110
# Do not use model.with_config(callbacks=...) here: it wraps the model in
# RunnableBinding and breaks ContextSummarizer._setup_model_profile (profile field).
# Langfuse callbacks for summarization LLM calls are propagated via the
# contextvar set in call_model (sync_langfuse_callbacks_from_config) before
# this runs; middleware wiring is tracked separately.
```
The function instantiates a temporary AgentState purely to reuse `manage_message_context` (which owns summarizer construction + sliding-window fallback), reads back `getattr(temp_state, message_list_name) or messages`, logs/tracks metrics, and swallows every exception into "return original messages".

**Flow:** caller with raw messages → temp AgentState → `manage_message_context` → summarized list read back from the named attribute → `_log_and_track_metrics` records `ContextSummarization`/`ContextSummarizationFailure` tracker steps → return. Any failure at ANY step → original messages returned.
**Invariant:** Summarization is best-effort everywhere outside the main loop — it may improve prompts but must never fail a run; observability callbacks ride a contextvar, not model wrapping, because `with_config` breaks profile assignment on the model object.

**Probe:** `tests/unit/test_context_summarizer.py` + integration `tests/integration/test_context_summarization.py` — pins summarize-or-original behavior through the temp-state path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "apply_context_summarization temp AgentState manage_message_context", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the throwaway-state pattern to share one summarization implementation between graph and non-graph callers, and the never-wrap-the-model-with-config constraint (callbacks via contextvar instead). Adapt the state class/attribute name. Omit the three-list fan-out if you have a single history. Direct tests exist.
