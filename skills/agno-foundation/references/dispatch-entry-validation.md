<!-- capsule-v2 -->
# Dispatch entry validation — What must be validated and initialized before a run can start?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** What does the public entrypoint check before spawning a run, in what order, so porters don't skip the loud-failure guards?

## run_dispatch: fail loudly on mode mismatches, normalize hooks exactly once
**Path/Symbol:** `libs/agno/agno/agent/_run.py:run_dispatch` (:1295-1472).
**Signature:** `run_dispatch(agent, input, *, stream=None, stream_events=None, user_id=None, session_id=None, session_state=None, run_context=None, run_id=None, audio=None, images=None, videos=None, files=None, knowledge_filters=None, add_history_to_context=None, add_dependencies_to_context=None, add_session_state_to_context=None, dependencies=None, metadata=None, output_schema=None, yield_run_output=None, debug_mode=None, **kwargs)`.
**Data Shape:** accepts str | List | Dict | Message | BaseModel | List[Message]; returns RunOutput or an iterator of events (chosen by resolved opts.stream); mints `run_id = run_id or str(uuid4())` BEFORE anything else.

### Decisive source
```python
if has_async_db(agent):
    raise RuntimeError("`run` method is not supported with an async database. Please use `arun` method instead.")
run_id = run_id or str(uuid4())
...
if not agent._hooks_normalised:
    if agent.pre_hooks:
        agent.pre_hooks = normalize_pre_hooks(agent.pre_hooks)
    if agent.post_hooks:
        agent.post_hooks = normalize_post_hooks(agent.post_hooks)
    agent._hooks_normalised = True
...
opts.apply_to_context(
    run_context,
    dependencies_provided=dependencies is not None,
    knowledge_filters_provided=knowledge_filters is not None,
    metadata_provided=metadata is not None,
)
```

**Flow:** async-DB guard → mint run_id → validate input against `agent.input_schema` → one-time hook normalization (idempotent via `_hooks_normalised` flag) → initialize session → initialize agent → media object-id validation → build RunInput → read-or-create session + update_metadata BEFORE option resolution (so session-stored metadata is visible) → resolve_run_options → build/merge RunContext (explicit args > existing run_context > resolved defaults, with *_provided flags preventing explicit-None from being overridden) → get_response_format only when no parser_model → construct RunOutput + start metrics timer → branch to `_run_stream` or `_run` passing the pre-read session as `pre_session`.
**Invariant:** The pre-read session flows into `_run` as `pre_session` so attempt 0 never reads the session twice; a porter who drops this re-reads per dispatch AND per attempt. `response_format` is suppressed when `parser_model` is set because structuring happens in a separate second-stage model call.
**Probe:** `grep -n 'has_async_db' libs/agno/agno/agent/_run.py` → guard at :1325 raising RuntimeError before any state mutation; direct behavior tests `libs/agno/tests/unit/agent/test_unified_continue.py::TestInputAppend` (input validation path) and `libs/agno/tests/integration/agent/test_agent_run_cancellation.py::test_cancel_non_existent_agent_run`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "run_dispatch resolve_run_options apply_to_context", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the guard ordering (async/sync mismatch raised before any side effect) and the one-time normalization flag pattern; adapt the option-precedence merge to your context object; omit AG-UI client_tools plumbing if you have no frontend-executed tools.
