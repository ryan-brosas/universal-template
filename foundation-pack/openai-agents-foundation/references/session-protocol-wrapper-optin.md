<!-- capsule-v2 -->
# Session protocol & wrapper opt-in — how do legacy session implementations gain run-context awareness without breaking the released interface?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** How does the runner decide whether a `Session` accepts a `wrapper` kwarg, and what makes a compaction-aware session?

## Structural protocol + signature introspection
**Path/Symbol:** `src/agents/memory/session.py:` `Session` Protocol (:16–56), `OpenAIResponsesCompactionArgs` (:109–131), `is_openai_responses_compaction_aware_session` (:142–152), `_session_method_accepts_wrapper` (:155–172), `_get_session_wrapper` (:189–196), `_call_session_method` (:199–212).
**Signature:** `def _session_method_accepts_wrapper(method: Any) -> bool`.
**Data Shape:** wrapper pass-through is all-or-nothing per SESSION: every one of get_items/add_items/pop_item/clear_session must declare a `wrapper` parameter (positional-or-keyword or keyword-only).

### Decisive source
```python
return any(
    parameter.name == "wrapper"
    and parameter.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    for parameter in parameters
)
...
if wrapper is not None and _session_method_accepts_wrapper(method):
    kwargs["wrapper"] = wrapper
result = method(*args, **kwargs)
if inspect.isawaitable(result):
    return await result
```
Compaction args TypedDict: `response_id`, `compaction_mode ∈ {previous_response_id, input, auto}`, `store`, `force`. Compaction detection is capability-based (`callable(getattr(session, "run_compaction", None))`) — no isinstance required.

**Flow:** runner calls sessions only through `_call_session_method`/`_get_session_wrapper` → introspection decides per method whether the current RunContextWrapper flows in → awaitable-or-sync results normalized. Legacy sessions keep byte-identical signatures; context-aware ones receive the same wrapper instance on every history op (so retries rewind within one scope).

**Invariant:** Opt-in must be COMPLETE (all four ops) or the wrapper silently degrades to None — partial support would let some calls see context others miss; the public protocol shape never changes.

**Probe:** `tests/memory/test_session_context_wrapper.py::test_session_wrapper_method_requires_named_wrapper_parameter` (:432), `test_session_wrapper_opt_in_requires_all_history_operations` (:454), `test_runner_does_not_treat_legacy_kwargs_as_wrapper_opt_in` (:180).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "session wrapper opt-in call session method compaction aware", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt signature-introspected capability injection for any long-lived plugin interface gaining a new optional parameter; adapt method sets to your CRUD; omit compaction typing if your backend has none.
