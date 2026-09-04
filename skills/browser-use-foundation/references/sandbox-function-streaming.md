<!-- capsule-v2 -->
# Sandbox function streaming — compile a local async fn into a cloudpickle payload + SSE result stream

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** how do you run a developer-written local Python function (with its closures, globals, and self-attributes) on a remote machine without shipping a package or defining an RPC protocol?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/sandbox/sandbox.py` (669 lines): `sandbox()` decorator (:215-530), `_extract_all_params` (:159-212), `_get_function_source_without_decorator` (:50-62), `_get_imports_used_in_function` (:65-156), `_parse_with_type_annotation` (:533+); `browser_use/sandbox/views.py` `SSEEvent.from_json` (:87-116) + typed data models (:26-63).
**Signature:** decorator turns `(browser: BrowserSession, **P) -> T` into ((**P) -> Coroutine[T]`: validates a `browser` param exists and its annotation string contains `Browser`, then every CALL rebuilds the function as source text + base64(cloudpickle(params)) streamed over one POST.
**Data Shape:** pydantic SSE envelope `{type, data, timestamp}`; data discriminated by `type` into `BrowserCreatedData{session_id,live_url,status}` / `LogData{message,level=stdout|stderr|info}` / `ResultData{execution_response:{success,result,error,traceback}}` / `ErrorData{error,traceback,status_code=500}`; unknown types degrade to raw dict.

### Decisive source
```python
# param capture: explicit args + closure cells + referenced globals, browser excluded
bound_args = sig.bind_partial(*args, **kwargs); bound_args.apply_defaults()
if param_name == 'self' and hasattr(param_value, '__dict__'):
    all_params.update(param_value.__dict__)          # self attrs become flat vars
for name, value in zip(func.__code__.co_freevars, [c.cell_contents for c in func.__closure__]):
    if name not in all_params: all_params[name] = value
for name in func.__code__.co_names:
    if name not in all_params and name in func.__globals__: all_params[name] = func.__globals__[name]

# import pruning: co_names + recursive annotation names (incl pydantic generics) -> keep only needed imports
pydantic_meta = getattr(annotation, '__pydantic_generic_metadata__', None)

# codegen: unpickle -> inject non-signature params as module vars -> original source -> thin runner
execution_code = f'''...
_params = cloudpickle.loads(base64.b64decode({repr(pickled_params)}))
{var_name} = _params['{var_name}']   # closure/global injections
{func_source}
async def run(browser):
    return await {func.__name__}(browser=browser, **{{k: _params[k] for k in {list(explicit_params.keys())!r}}})'''

# transport: ONE streaming POST, 30-min budget, sentinel separates no-result from falsy result
_NO_RESULT = object()
async with httpx.AsyncClient(timeout=1800.0) as client:
    async with client.stream('POST', url, json={'code': b64(execution_code), 'env': env}, headers={'X-API-Key': api_key}) as response:
        async for line in response.aiter_lines():
            if not line.startswith('data: '): continue
            event = SSEEvent.from_json(line[6:])   # RESULT success -> capture; else raise SandboxError

# wrapper signature surgery hides the injected browser param from callers
wrapper.__signature__ = sig.replace(parameters=[p for p in sig.parameters.values() if p.name != 'browser'])
```

**Flow:** decorate-time validation -> call time: API key check -> capture params (explicit/self/closure/globals) -> AST-strip decorators from source -> prune module imports to those actually referenced -> cloudpickle+base64 params -> assemble single-file remote script with module-var injections -> POST to `https://sandbox.api.browser-use.com/sandbox-stream` -> parse `data:` SSE lines -> BROWSER_CREATED shows live_url once; LOG routes stdout/stderr/info; INSTANCE_READY fires callback; RESULT success captures raw result else raises `SandboxError`; ERROR raises after fail-open callback -> re-type result against original return annotation recursively -> return.
**Invariant:** callbacks NEVER break the stream (each wrapped try/except prints a warning and continues); malformed JSON lines are skipped, never fatal; RemoteProtocolError/ReadError/StreamClosed are ALWAYS fatal `SandboxError` because the handshake is assumed deterministic; a missing final event raises "No result received"; falsy results survive via the `_NO_RESULT` sentinel; the local function object is never executed locally.
**Probe:** from repo root, build a closure-carrying annotated function and run the three pure helpers (`_get_function_source_without_decorator`, `_get_imports_used_in_function`, `_extract_all_params`); assert exactly the needed imports/params come out (executed this pass; output in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "sandbox decorator cloudpickle SSE stream execute", file_pattern: "browser_use/sandbox/*", limit: 12 });
```

## Verdict
Adopt this shape for any "run my code elsewhere" feature: AST-derived source plus cloudpickle context capture beats RPC scaffolding for agent tooling. Keep the SSE vocabulary small and type-discriminated; make user callbacks fail-open while transport failures stay fatal; use a sentinel, not Optional[None], to separate "no result" from "falsy result". Adapt import-pruning to your runtime; do NOT port the hardcoded vendor URL/key plumbing.
