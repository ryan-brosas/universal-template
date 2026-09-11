<!-- capsule-v2 -->
# API app-factory & boot plane — how does the FastAPI wrapper get built, what does boot actually execute, and which pieces are dead at this pin?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0 — source-available; SaaS-competing-use restricted) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** Where should a porter wire CORS/prefix/workers when wrapping the orchestrator in FastAPI, and what in this module must NOT be trusted as the boot path?

## get_app factory + constants + dead subprocess streamer + broken __main__
**Path/Symbol:** `core/server/api_routes.py`: constants `APP_VERSION/APP_NAME/API_PREFIX/IS_DEBUG/HOST/PORT/WORKERS` (:25-31), `get_ist_time` (:39-46), `calculate_duration` (:48-53), `get_app` (:55-65), `app = get_app()` (:67), `stream_subprocess_output` (:69-93, graph in=0/out=0 — dead at pin), `__main__` block (:185-187). Boot truth: `Dockerfile:12` `CMD ["uvicorn", "core.server.api_routes:app", "--loop", "asyncio", "--host", "0.0.0.0", "--port", "8000"]` (container overrides the module-default PORT=8080).
**Signature:** `def get_app() -> FastAPI` — builds `FastAPI(title=APP_NAME, version=APP_VERSION, debug=IS_DEBUG)` then `add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])`.
**Data Shape:** Module-level singleton `app`; env knobs HOST (default `0.0.0.0`) and PORT (default `8080`); `WORKERS = 1` hardcoded (process-local `active_tasks` registry makes this load-bearing — see sse-task-api).

### Decisive source
```python
# :58-64 — permissive-by-default CORS
fast_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
# :185-187 — BROKEN AS SHIPPED: no module named "main" exposes `app`
if __name__ == "__main__":
    logger.info("**********Application Started**********")
    uvicorn.run("main:app", host=HOST, port=PORT, workers=WORKERS, reload=IS_DEBUG, log_level="info")
```

**Flow:** import builds `app` via factory → Docker boots `uvicorn core.server.api_routes:app` → routes register on bare paths (`@app.post("/execute_task")`). `API_PREFIX = "/api"` is defined but NEVER used — no router prefix, no mount. `stream_subprocess_output` (dual-stream readline gather with real-time terminal echo) has zero graph edges: no route or caller reaches it; kept from an earlier CLI-runner life.
**Invariant:** The REAL boot contract is the Dockerfile's fully-qualified `core.server.api_routes:app`; the `__main__` `"main:app"` string cannot import (`main.py` defines a `main()` coroutine, not an ASGI app) — never cite the `__main__` block as the entry path. `allow_origins=["*"]` TOGETHER WITH `allow_credentials=True` is an insecure combination browsers refuse to honor for credentialed requests; porters must narrow origins.
**Probe:** `cd $REFERENCE_ROOT/TheAgenticBrowser && grep -n "main:app" core/server/api_routes.py` → `:187`; `grep -rn "API_PREFIX" core/ --include='*.py'` → definition-only (`api_routes.py:27`); `grep -c "stream_subprocess_output" core/server/api_routes.py` → `1` (declaration only — no internal or external caller); `grep -n "api_routes:app" Dockerfile` → `:12` (full CMD also carries `--loop asyncio` and port 8000, overriding module default 8080). Coverage caveat: repo ships no tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "get_app FastAPI CORSMiddleware stream_subprocess_output", limit: 10 });
```

## Verdict
Adopt: tiny app-factory + module-singleton pattern over a process-local task registry; IST/duration helpers as presentation-side utilities. Adapt: CORS to an explicit origin list, add your real auth layer (this plane has none — see error-envelope/sse capsules for the task lifecycle). Fix-at-port: either mount routes under `API_PREFIX` or delete the constant; delete `stream_subprocess_output`; correct the `__main__` target if you keep one. Omit: nothing else structural. Caveat: no upstream tests; graph coverage `no_recorded_issue` at generation `2026-08-23T00:02:33Z`.
