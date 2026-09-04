<!-- capsule-v2 -->
# Tool assembly pipeline — How do declared, default, and client tools become model-ready Functions with media injected?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** What is the resolution order for tools per run, and why is media collection conditional?

## get_tools composes the pool; determine_tools_for_model parses + injects context
**Path/Symbol:** `libs/agno/agno/agent/_tools.py:get_tools` (:112-217) → `determine_tools_for_model` (:528-571).
**Signature:** `get_tools(agent, run_response, run_context, session, user_id=None) -> List[Union[Toolkit, Callable, Function, Dict]]`; `determine_tools_for_model(agent, model, processed_tools, run_response, run_context, session, async_mode=False) -> List[Union[Function, dict]]`.
**Data Shape:** composition order = resolved callable factories → AG-UI client_tools → memory/learning/culture/state default tools (each gated on its enable flag) → knowledge search tool (only when knowledge/retriever exists AND search_knowledge) → add_to_knowledge → skills; then parse_tools flattens Toolkits/callables/dicts into Function records.

### Decisive source
```python
# determine_tools_for_model — media injection is CONDITIONAL:
needs_media = any(
    any(param in signature(func.entrypoint).parameters for param in ["images", "videos", "audios", "files"])
    for func in _functions
    if isinstance(func, Function) and func.entrypoint is not None
)
# Only collect media if functions actually need them
joint_images = collect_joint_images(run_response.input, session) if needs_media else None
...
for func in _functions:
    if isinstance(func, Function):
        func._run_context = run_context
        func._images = joint_images
```

Sync guard (`raise_if_async_tools`, :53-110): every concrete tool list entering a SYNC run is scanned with `iscoroutinefunction` and raises "Async tool … can't be used with synchronous agent.run()" — async entrypoints are a mode error, not an await problem.
**Flow:** per-run factory resolution (`resolve_callable_tools`) means the tool POOL itself can be dynamic per context → flag-gated defaults appended (read_chat_history / read_tool_call_history / search_past_sessions pairs / update_user_memory / learning tools / cultural knowledge / update_session_state) → knowledge search unified through `create_knowledge_search_tool` (knowledge_retriever first, fallback to knowledge.search) → parse_tools converts to Function schemas → signature inspection decides media collection → `_run_context` + media bound onto each Function instance.
**Invariant:** Media is collected ONCE per run and only when some entrypoint's signature names media params — unconditional collection would deep-copy session media on every turn. The sync/async tool check happens at RESOLUTION time (before messages are built), failing loudly instead of mid-model-loop.
**Probe:** `grep -c 'def raise_if_async_tools' libs/agno/agno/agent/_tools.py` → **1** (+`_raise_if_async_tools_in_list` twin); direct behavior test coverage via unit suite `libs/agno/tests/unit/agent/test_unified_continue.py::TestResumeRunWithCompletedToolsNoRequirements::test_resume_run_with_completed_tools_no_requirements` (:187).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "get_tools determine_tools_for_model needs_media", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt flag-gated composition order + signature-driven conditional media injection; adapt Toolkit/Function parsing to your schema layer; omit AG-UI client_tools if you have no frontend-executed functions.
