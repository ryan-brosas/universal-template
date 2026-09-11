<!-- capsule-v2 -->
# Three-mode code execution dispatch — why does the SAME generated code need three different async wrappers, and which mode wins when two flags are set?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Generated agent code is full of `await` statements, but it must run identically in a cloud sandbox, an in-process exec, and a Docker container — how does one entry point serve all three?

## Wrapper-per-runtime dispatch with E2B > local > docker priority
**Path/Symbol:** `src/cuga/backend/tools_env/code_sandbox/sandbox.py` — `run_code` :333-472 (mode flags :369-370, priority comment :375, wrapper selection :376-384); three wrappers: `wrapped_code` (indent-everything into `async def __cuga_async_wrapper__()`), `wrapped_code_with_call` (+`\nasyncio.run(__cuga_async_wrapper__())` for sync container context), `wrapped_code_e2b` (+ `async def main(): await __cuga_async_wrapper__()` + `if __name__ == "__main__": await main()` — E2B's runner supports top-level await, plain asyncio.run would double-run).
**Signature:** `run_code(code, state, _locals=None) -> tuple[str_output, dict]`; composition = `get_premable(...) + variables + wrapped_final` (:386-396) — preamble injects the registry URL and clock-freeze BEFORE user code.
**Data Shape:** Preamble contract: `call_api(app_name, api_name, args)` helper POSTs `{function_name, app_name, args}` to `{registry_host}/functions/call?trajectory_path=...`, 30s timeout, run in executor off the event loop; optional `MyDateTime` class replaces `datetime.datetime.now()` with tracker's frozen current_date (benchmark determinism).

### Decisive source
```python
# sandbox.py:376-384 — priority is documented IN CODE because it surprises people
# Choose the right wrapper based on execution mode
# Priority: E2B > Local > Docker (E2B takes precedence even if local is also enabled)
if is_e2b:
    wrapped_final = wrapped_code_e2b       # E2B uses async main pattern
elif is_local:
    wrapped_final = wrapped_code           # Local: no call — caller awaits from namespace
else:
    wrapped_final = wrapped_code_with_call # Docker: asyncio.run from sync context
```
Validation asymmetry (:401-408): pre-execution `compile()` validation runs for local/docker but is SKIPPED for E2B because its wrapper relies on top-level await which needs special compile flags — E2B validates at run time instead.

**Flow:** format variables from state → build all three wrapper variants → select by flags → prepend preamble+variables → validate (non-E2B) → persist source file under LOGGING_DIR when tracker enabled → dispatch: E2B (`execute_code_in_e2b`, thread-scoped warm cache) / local (`run_local`) / docker (`SandboxSession` on detected socket). Return contract: stdout if exit 0 else stderr — errors travel as stderr text, not exceptions.
**Invariant:** The SAME code text must remain valid across modes — never emit mode-specific syntax inside user code; mode differences live ONLY in the generated wrapper shell. Registry URL choice follows the runtime: remote sandboxes can't reach localhost, so E2B requires `function_call_host`/`registry_host` config and falls back to a URL that will fail LOUDLY with an explanatory log rather than silently timing out (:86-98). Appworld-benchmark post-processing runs only on the matching benchmark flag, per branch.
**Probe:** direct tests `code_sandbox/tests/test_sandbox.py` — `TestRunLocal` pins exception taxonomy of the local path (syntax error exit 1 + caret message :9-21, NameError/TypeError/ZeroDivision/Import/Index/KeyError/Attribute/custom/nested-traceback/mixed-stdout-stderr/SystemExit-with-code, success stdout purity :182-199). Coverage caveat: docker/E2B branches untested in CI (require daemon/credentials).
**Retrieve:** `await mcp.codebaseMemory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "run_code get_premable __cuga_async_wrapper__ e2b_sandbox local_sandbox", limit: 10 });`

## Verdict
Adopt one dispatcher emitting runtime-specific async wrappers around unchanged user code, strict E2B>local>docker precedence, and skip-validation-for-top-level-await. Adapt the preamble to your tool-invocation protocol. Omit the clock-freeze unless you run deterministic benchmarks.
