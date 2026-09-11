<!-- capsule-v2 -->

# Runtime-entrypoint flow loading — Which env var overrides storage lookup, and what happens on a missing flow?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `ext-prefect`. **Question:** How does an infrastructure-spawned process load the right flow without trusting the server's copy?

**Path/Symbol:** `src/prefect/flow_engine.py:load_flow (242-251)` + `_load_flow_from_runtime_entrypoint (235-239)` + `load_flow_run/load_flow_and_flow_run (229-257)`; consumer `_run_flow_from_runtime_entrypoint (:260-278)`.

**Signature:** `_load_flow_from_runtime_entrypoint(entrypoint: str) -> Flow[..., Any]`; fallback `load_function_and_convert_to_flow(entrypoint)`.

**Data Shape:** Env override `PREFECT__FLOW_ENTRYPOINT` (set by the spawning runner); otherwise async `load_flow_from_flow_run(flow_run, use_placeholder_flow=False)` resolves from deployment storage.

### Decisive source
```python
def _load_flow_from_runtime_entrypoint(entrypoint: str) -> Flow[..., Any]:
    try:
        return load_flow_from_entrypoint(entrypoint, use_placeholder_flow=False)
    except MissingFlowError:
        return load_function_and_convert_to_flow(entrypoint)

def load_flow(flow_run: FlowRun) -> Flow[..., Any]:
    entrypoint = os.environ.get("PREFECT__FLOW_ENTRYPOINT")
    if entrypoint:
        flow = _load_flow_from_runtime_entrypoint(entrypoint)
    else:
        flow = run_coro_as_sync(
            load_flow_from_flow_run(flow_run, use_placeholder_flow=False)
        )
    return flow
```

**Flow:** child process starts → `_main` validates `PREFECT__FLOW_RUN_ID` as UUID (malformed ⇒ exit 1 BEFORE any orchestration) → load_flow_run via sync client → load_flow: env-entrypoint path imports the module directly (`use_placeholder_flow=False` so failures are real, never silent placeholders); MissingFlowError degrades to converting a plain function reference into a Flow — any OTHER exception logs "Unexpected exception encountered when trying to load flow" with traceback and re-raises → RunMetrics wraps run_flow + `_drive_run_flow_result`.

**Invariant:** (1) The env var WINS over the flow-run's stored definition — the runner that spawned the container is authoritative about which code to execute; a porter who reverses this precedence executes stale code after redeploys. (2) Only MissingFlowError converts; import errors inside the target module must surface loudly rather than masquerade as "not a flow". (3) `use_placeholder_flow=False` in BOTH paths guarantees no placeholder object reaches the engine.

**Probe:** `grep -cF 'load_flow_from_entrypoint(entrypoint, use_placeholder_flow=False)' src/prefect/flow_engine.py` → 1. Direct tests: entrypoint-loading suites under `tests/test_flows.py` (`load_flow_from_entrypoint`) plus runtime-shell coverage via `tests/runner/` starter-engine tests.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-prefect", "query": "load_flow_from_runtime_entrypoint MissingFlowError", "limit": 3}'
```

## Verdict
Adopt env-authoritative code resolution with narrow conversion fallback for any deploy-from-source runner; adapt entrypoint format; omit deployment storage negotiation.
