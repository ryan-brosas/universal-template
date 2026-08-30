<!-- capsule-v2 -->
# Registry URL ladder — why does a sandbox preamble get THREE different registry hosts depending on where it will run?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Generated code inside any execution runtime must call back into the host's tool registry — but localhost, Docker, and cloud sandboxes each reach the host differently. How do you pick the URL?

## Runtime-aware host resolution with loud-failure fallback
**Path/Symbol:** `src/cuga/backend/tools_env/code_sandbox/sandbox.py` — `get_premable(is_local, current_date, for_e2b)` :78-206; E2B branch :86-99 (`function_call_host` → `registry_host` → hard-coded `http://localhost:8001` + logger.error telling the operator to use ngrok); configured-host branch :100-105; default branch :107-116 (local → `get_registry_base_url()`; container → `http://host.docker.internal:{registry_port}`); trajectory threading via `quote(tracker.get_current_trajectory_path())` query param on every variant; structured-tool injection :119-127 (only when `local_sandbox` AND tracker holds tools — otherwise emits NOTHING and logs "Structured tools not enabled").
**Signature:** `get_premable(...) -> str` (executable Python source text); final call target `{base}/functions/call?trajectory_path={quoted}`.
**Data Shape:** The preamble embeds: imports, optional tracker import/init/invocation snippets (the invocation wrapper coerces results to dicts via `model_dump`/`__dict__`/`asdict` ladders and SWALLOWS `"not found"` ValueErrors), optional clock freeze, and an async `call_api` that POSTs `{function_name, app_name, args}` with 30s timeout via `loop.run_in_executor`.

### Decisive source
```python
# sandbox.py:92-98 — E2B cannot reach your localhost; failing LOUDLY beats silent hang
if not function_call_url:
    logger.error(
        "E2B sandbox requires a publicly accessible URL. "
        "Please set 'function_call_host' or 'registry_host' in settings.toml. "
        "You can use ngrok or expose your registry server (port 8001) to the internet.")
    function_call_url = "http://localhost:8001"  # Will fail but at least show the issue
```
The deliberate bad-default converts a confusing remote timeout into an immediate, self-documenting connection-refused — the comment says so verbatim.

**Flow:** `run_code` calls `get_premable(is_local=is_local or is_e2b, for_e2b=is_e2b)` — note BOTH local and E2B take the non-Docker URL style since neither runs inside the compose network — then concatenates preamble + variables + wrapper. The same preamble builder is called TWICE (:386-396 for execution, :410-420 for the persisted source file) so on-disk artifacts match what actually ran.
**Invariant:** Host selection is a property of the RUNTIME, not the config alone — Docker containers need `host.docker.internal`, cloud needs a public host, only in-process/local may use loopback. Trajectory path must be URL-quoted (it contains slashes). Structured-tool injection must be all-or-nothing per preamble: a half-injected tool surface would produce NameError mid-task.
**Probe:** coverage caveat — no direct test file covers `get_premable`; nearest pins are `test_sandbox.py::TestRunLocal` (execution half) and the live-gated E2E suites. Verify by reading :78-127 before porting; the branch conditions are the contract.
**Retrieve:** `await mcp.codebaseMemory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "get_premable function_call_host registry_base_url call_api", limit: 10 });`

## Verdict
Adopt runtime-keyed URL selection with the loud-failure fallback and quoted trajectory propagation. Adapt hosts to your network topology. Omit the structured-tool snippet if your sandbox gets tools another way.
