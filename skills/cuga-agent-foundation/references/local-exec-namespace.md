<!-- capsule-v2 -->
# In-process code exec namespace — why exec into a namespace seeded with `sys.modules`, and how do SystemExit, syntax errors, and async bodies become (exit_code, stdout, stderr)?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** You want sandbox-free local execution of LLM-generated async code with real stdout/stderr capture and process-safe failure semantics — what does the exec harness actually have to handle?

## Namespace-seeded exec + exception-to-result funnel
**Path/Symbol:** `src/cuga/backend/tools_env/code_sandbox/sandbox.py` — `run_local` :216-309; namespace construction :224-239 (dunders + `importlib`/`asyncio`/`concurrent` + `namespace.update(sys.modules)`); compile-with-caret SyntaxError :244-252; wrapper await :256-260 (`asyncio.iscoroutinefunction` guard before awaiting `__cuga_async_wrapper__`); funnel: `SystemExit` :261-266 (exit_code = `e.code if e.code is not None else 0`, message WRITTEN to stderr buffer), SyntaxError :267-285 and generic Exception :286-305 (exit 1 + full traceback appended to stderr buffer); pre-validation twin `validate_and_clean_code` :312-330 returns `(code, error_message)` without executing.
**Signature:** `run_local(code_content) -> ExecutionResult(exit_code:int, stdout:str, stderr:str)`; output via `redirect_stdout/redirect_stderr(StringIO)` — capture happens at the PROCESS level, so prints from any imported module are captured too.
**Data Shape:** The executed file is `preamble + variables + wrapped_code` where user code sits INSIDE `async def __cuga_async_wrapper__():` — top-level awaits in generated code become ordinary awaits inside the function body.

### Decisive source
```python
# sandbox.py:261-266 — exit() in generated code is DATA, not a crash
except SystemExit as e:
    exit_code = e.code if e.code is not None else 0
    logger.warning(f"SystemExit caught in code execution: exit_code={exit_code}")
    stderr_buffer.write(f"Generated Code called exit with code : {exit_code}")
```
Why this matters: an LLM that emits `exit(1)` inside a task script must not kill the agent server. In-process exec means ALL exceptions are yours to catch — the funnel converts every failure class into the same `(exit_code, stdout, stderr)` shape the container backends naturally produce, keeping downstream handling uniform.
```python
# sandbox.py:237-239 — the line that makes imports work
# Add all currently loaded modules to the namespace
# This ensures that any modules already imported in the main program are available
namespace.update(sys.modules)
```
Generated code calling `tracker.invoke_tool(...)` or importing project modules works because the host's module cache IS the sandbox namespace — zero re-import cost, but also zero isolation: host state is reachable and mutable.

**Flow:** build namespace → compile (syntax errors get Line/offset caret formatting BEFORE any execution) → exec → if the wrapper coroutine exists, await it under the redirect context → classify exception (SystemExit vs SyntaxError vs other) → return buffers.
**Invariant:** Never let an exception class escape run_local — callers branch on exit_code only. `sys.modules` seeding trades isolation for capability; anything requiring real isolation must use the docker/E2B branches instead (this function is the `local_sandbox` feature flag's backend). Awaiting must be guarded by `iscoroutinefunction` because non-async snippets produce no wrapper.
**Probe:** direct tests `code_sandbox/tests/test_sandbox.py::TestRunLocal` — 20+ cases pinning exact stderr substrings per exception type (`"expected ':'"` in syntax :21, `"No module named"` import :84, partial-stdout-before-raise preserved :446-465, deep-nested traceback levels visible :467-495, success leaves stderr EMPTY :199). This suite is the behavior contract for the whole funnel.
**Retrieve:** `await mcp.codebaseMemory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "run_local ExecutionResult validate_and_clean_code __cuga_async_wrapper__", limit: 10 });`

## Verdict
Adopt the sys.modules-seeded namespace ONLY when you accept its no-isolation trade, the three-class exception funnel with uniform result shape, and process-level stdout capture. Adapt dunders to your embedding. Omit entirely if you always execute in real sandboxes.
