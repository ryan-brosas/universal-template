<!-- capsule-v2 -->
# system-user-id-source-split — Why does the same run resolve two different "user ids" for system variables?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** Which identity feeds workflow system variables, and when?

## External calls use the EndUser session id; internal calls use the account id
**Path/Symbol:** `api/core/app/apps/workflow/app_generator.py:_generate_worker` (:658-670); consumers `build_system_variables(files, user_id=system_user_id, ...)` in `api/core/app/apps/workflow/app_runner.py` (:114-121) and pipeline construction in `generate_task_pipeline.py:__init__` (:112-118).
**Signature:** local resolution inside `_generate_worker` before constructing `WorkflowAppRunner`.
**Data Shape:** `is_external_api_call = invoke_from in {InvokeFrom.WEB_APP, InvokeFrom.SERVICE_API}`; external ⇒ `end_user.session_id` (empty string if row vanished); internal ⇒ `application_generate_entity.user_id`.

### Decisive source
```python
# Determine system_user_id based on invocation source
is_external_api_call = application_generate_entity.invoke_from in {
    InvokeFrom.WEB_APP,
    InvokeFrom.SERVICE_API,
}

if is_external_api_call:
    # For external API calls, use end user's session ID
    end_user = session.scalar(select(EndUser).where(EndUser.id == application_generate_entity.user_id))
    system_user_id = end_user.session_id if end_user else ""
else:
    # For internal calls, use the original user ID
    system_user_id = application_generate_entity.user_id
```

**Flow:** worker loads workflow → resolves which identity string represents "the user" for THIS run kind → passes it into `build_system_variables` (becomes `sys.user_id` visible to nodes) and into response converters. Web/end-user runs expose a stable anonymous session identifier; console/debug/API-key runs carry the account id.
**Invariant:** The split happens ONCE in the worker — runners/pipelines never re-derive it; a missing EndUser row degrades to empty string rather than raising (system variable must exist); privacy posture: external consumers never see account ids because the mapping never selects them.
**Probe:** `grep -c 'system_user_id' core/app/apps/workflow/app_generator.py` → 3.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "_generate_worker system_user_id end_user session_id", limit: 10 });
```

## Verdict
Adopt one resolution point for the system-variable identity with source-dependent semantics. Adapt the surface enumeration. Omit nothing else.
