<!-- capsule-v2 -->
# Filter pipeline contract — in what order do filter plugins run, and how are their params and valves bound?

**Source:** open-webui "Open WebUI License" `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** How is the filter execution order derived, which params does each handler receive, and how do valves and file-handling flags flow through the pipeline?

## (priority, id) ordering with signature-filtered params
**Path/Symbol:** `backend/open_webui/utils/filter.py:resolve_filter_pipeline` (56-94), `get_model_filter_ids` (47-53), `process_filter_functions` (197-235), `process_filter_function` (153-192), `get_filter_params` (123-132), `FilterContext` (11-29), `apply_user_valves` (135-144).
**Signature:** `async def resolve_filter_pipeline(request, model: dict, enabled_filter_ids: list = None) -> (filter_ids, functions)` · `async def process_filter_functions(request, filter_context, filter_functions, filter_type, form_data, extra_params) -> (form_data, {})`.
**Data Shape:** candidates = global active filters ∪ `model.info.meta.filterIds`, intersected with active; per-request `FilterContext` memoizes batch-fetched function valves (`Functions.get_function_valves_by_ids`) and per-`(filter_id, user_id)` user valves.

### Decisive source
```python
async def get_priority(function_id):
    ...
    valves = function_module.Valves(**(valves_db if valves_db else {}))
    return getattr(valves, 'priority', 0)
filter_ids.sort(key=lambda fid: (priorities.get(fid, 0), fid))   # line 91

def get_filter_params(sig, filter_id, filter_type, form_data, extra_params):
    params = {'event': form_data} if filter_type == 'stream' else {'body': form_data}
    return params | {k: v for k, v in {**extra_params, '__id__': filter_id}.items()
                     if k in sig.parameters}          # only declared params injected
```
and the fold:
```python
function_module = await get_function_module(
    request, filter_id, load_from_db=(filter_type != 'stream'), function=function)  # line 166
handler = getattr(function_module, filter_type, None)
if not handler: return form_data, valves_by_id, None      # missing hook = passthrough
...
skip_files = skip_files or file_handler                   # OR-accumulated inlet flag
...
if skip_files: del form_data['metadata']['files']; del form_data['files']
```
**Flow:** toggle-able filters are dropped unless present in `enabled_filter_ids` → priorities read from each module's `Valves.priority` (exception-safe default 0), precomputed because async sort keys are illegal → ascending `(priority, id)` order is total and deterministic → sequential fold mutates `form_data`; each handler gets only parameters it declares (`__id__` always available, plus whatever `extra_params` carries such as `__user__`/`__request__`) → `__user__` handlers get UserValves injected (failure logged, never fatal) → handler exceptions log at debug and re-raise.
**Invariant:** ordering never depends on dict/DB iteration order — it is the sorted `(priority, id)` tuple; a filter without the requested hook is a no-op; stream handlers reuse cached modules (no DB read per token) while inlet/outlet reload from DB with a content-hash short-circuit; valve lookups are batched once per request via FilterContext.
**Probe:** no test runner at this HEAD — deterministic anchors executed: `grep -n "priorities.get(fid, 0), fid)" backend/open_webui/utils/filter.py` hits line 91; `grep -n "load_from_db=(filter_type != 'stream')" backend/open_webui/utils/filter.py` hits line 166.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "resolve_filter_pipeline process_filter_functions valves priority signature", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the deterministic (priority, id) ordering, signature-filtered param injection, batched valve memoization, and the stream-vs-inlet module-loading split; adapt the Valves pydantic classes and FastAPI request plumbing to your host; omit open-webui's specific extra_params vocabulary. Coverage caveat: none recorded for these paths; direct tests absent repo-wide.
