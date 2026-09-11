<!-- capsule-v2 -->
# Langfuse trace propagation — how do you make nested LLM calls (reflection, shortlister, output formatter) share ONE Langfuse trace with the parent agent.invoke instead of spawning sibling root traces?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** CugaLite and policy enactment run LLM calls outside the main `call_model` path — how does a contextvar-based mechanism carry the parent's Langfuse callbacks/trace-id into those nested calls so Langfuse shows one trace per logical run?

## Contextvar-scoped callback propagation + trace-scoped handler subclass
**Path/Symbol:** `src/cuga/backend/cuga_graph/utils/langfuse_tracing.py:18-22` (ContextVars), `:40-55` (`collect_langfuse_callbacks_from_config`), `:58-65` (`set_langfuse_callbacks`/`set_langfuse_trace_id`), `:83-140` (`_trace_scoped_handler_class`), `:143-148` (`create_trace_langfuse_handler`), `:165-183` (`sync_langfuse_callbacks_from_config`), `:191-217` (`nested_langgraph_invoke_config`/`get_langfuse_invoke_config`), `:220-249` (`_langfuse_handler_classes`/`is_langfuse_callback_handler`).
**Signature:** `sync_langfuse_callbacks_from_config(config) -> None` (copies trace id, handlers, RunnableConfig into the async context); `get_langfuse_invoke_config() -> dict` (LangChain `config` for nested `ainvoke`); `create_trace_langfuse_handler(trace_id, *, parent_span_id=None) -> handler|None`.
**Data Shape:** ContextVars: `_langfuse_callbacks` (list|None), `_langfuse_trace_id` (str|None), `_langfuse_primary_handler` (handler|None), `_langgraph_run_config` (config|None). `is_langfuse_callback_handler(cb)` checks the class name against known Langfuse handler names AND isinstance against the lazily-imported handler classes (so it works even when the handler is subclassed).

### Decisive source
```python
# langfuse_tracing.py:95-119 — subclass that links orphan LLM runs to the eval trace id
class TraceScopedLangfuseCallbackHandler(base_cls):
    def _scoped_trace_context(self, parent_run_id):
        trace_ctx = getattr(self, "_trace_context", None)
        if trace_ctx is None:
            tid = _langfuse_trace_id.get()
            if tid: trace_ctx = _trace_context_for_id(tid)
        parent_missing = parent_run_id is None or parent_run_id not in getattr(self, "_runs", {})
        return trace_ctx if (trace_ctx is not None and parent_missing) else None
    def on_llm_start(self, serialized, prompts, *, parent_run_id=None, **kwargs):
        scoped = self._scoped_trace_context(parent_run_id)
        if scoped is None:
            return super().on_llm_start(...)
        original = self._trace_context
        self._trace_context = scoped
        try:
            return super().on_llm_start(...)
        finally:
            self._trace_context = original
```

**Flow:** `sync_langfuse_callbacks_from_config` copies the parent's trace id, Langfuse handlers, and RunnableConfig into the current async context (via ContextVars, so concurrent runs don't collide). `collect_langfuse_callbacks_from_config` flattens callback managers into handler instances and dedupes by `id()`, keeping only Langfuse handlers. When no callbacks are present but a trace id is, `get_langfuse_invoke_config` builds a `TraceScopedLangfuseCallbackHandler` that links orphan LLM runs to the eval trace id. The subclass overrides the PUBLIC entry points (`on_llm_start`/`on_chat_model_start`) — NOT the name-mangled private `__on_llm_action` — because overriding the mangled name would itself be mangled and never called by the base class. It temporarily swaps `_trace_context` around the super() call only when the parent run is missing (orphan), so tracked nested calls keep their real parentage.

**Invariant:** The handler-class detection is lazy (`_langfuse_handler_classes` imports on first use, tolerates ImportError) so the module works even when langfuse isn't installed. The name-mangling pitfall is the key porting trap: you cannot override the private dispatch method — you must override the public entry points and swap the trace context around the super() call. ContextVars keep concurrent async runs isolated.

**Probe:** `tests/unit/test_langfuse_tracing.py:207` (`test_attaches_orphan_llm_start_to_eval_trace`), `:220` (`test_attaches_orphan_chat_model_start_to_eval_trace`), `:233` (`test_does_not_override_tracked_nested_calls`), `:248` (`test_apply_callbacks_drops_agent_langfuse_when_trace_id_set`), `:308` (`test_nl_auto_continue_passes_invoke_config`), `:352` (`test_output_formatter_ainvoke_receives_callbacks`), `:400` (`test_shortlist_passes_explicit_run_config`), `:433` (`test_context_summarization_does_not_wrap_model_with_config`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "sync_langfuse_callbacks_from_config get_langfuse_invoke_config TraceScopedLangfuseCallbackHandler collect_langfuse_callbacks_from_config", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the contextvar-scoped callback/trace-id propagation, the lazy handler-class detection, and the trace-scoped handler subclass that swaps `_trace_context` around the public entry points (never the mangled private method). Adapt the trace-id source to your eval harness. Omit the LangGraph-specific `nested_langgraph_invoke_config` if you don't nest LangGraph invokes. Direct-test coverage is comprehensive.
