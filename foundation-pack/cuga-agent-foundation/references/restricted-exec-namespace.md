<!-- capsule-v2 -->
# Restricted exec namespace with benchmark kill-switch — how do you sandbox LLM-generated imports/builtins locally, and what must the escape hatch preserve?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** You execute generated code in-process — how do you restrict imports and builtins without breaking pandas/asyncio workflows, and how do benchmarks/skills opt out?

## Allowlist import shim + curated builtins; relaxed mode swaps in FULL builtins + sys/os, not an unguarded exec
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/executors/common/restricted_environment.py` — `RestrictedEnvironment.is_benchmark_mode` :10-17, `create_restricted_import(allowed_modules)` :19-41, `create_safe_builtins(restricted_import_func)` :43-123 (the curated allowlist), `create_restricted_globals(safe_builtins, safe_locals)` :125-181. Gate helper: `common/benchmark_mode.py` — `is_relaxed_execution() = is_benchmark_mode() or is_skills_relaxed_execution()` (contextvar per-run skills flag).
**Signature:** `create_restricted_import(allowed_modules: set) -> import-func`; `create_safe_builtins(fn) -> dict`; `create_restricted_globals(safe_builtins, safe_locals) -> dict` (always includes asyncio+json+pandas-as-pd/pandas when importable).
**Data Shape:** restricted globals = `{"__builtins__": safe_builtins, "asyncio", "json", ("pd"/"pandas"), **safe_locals}`.

### Decisive source
```python
# :36-39 — root-module allowlist check, then delegate to the REAL importer
def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name.split('.')[0] not in allowed_modules:
        raise ImportError(f"Import of '{name}' is not allowed in restricted execution context")
    return _original_import(name, globals, locals, fromlist, level)
```
```python
# :29-30 / :53-58 — relaxed execution returns __import__ itself and FULL builtins
if is_relaxed_execution():
    return __builtins__['__import__'] if isinstance(__builtins__, dict) else __builtins__.__import__
```
**Flow:** build restricted import over allowed set → curate ~50 safe builtins (types, iteration/math, introspection, exceptions, print, locals/vars, staticmethod, `__build_class__`, `__name__='__restricted__'`) → assemble globals. Relaxed (benchmark ≠ default OR skills contextvar): real `__import__`, full builtins copy, plus sys/os injected into globals.
**Invariant:** (1) The allowlist matches ROOT modules only (`name.split('.')[0]`) so `pandas.api` passes when `pandas` is allowed. (2) Relaxed mode is a DELIBERATE superset (adds sys/os), not a different code path through the executor — same funnel, wider namespace. (3) `__builtins__` is a dict in some embeddings and a module in others — every access handles both. (4) This is NOT a security boundary against hostile code (in-process); it's a mistake-guard for LLM code — hostile-code isolation lives in remote/docker executors.

**Probe:** No direct unit suite at HEAD for restricted_environment.py (coverage caveat — composition layer under the local executor whose failure semantics are pinned by tests around tools_env/code_sandbox/sandbox.py run_local and SecurityValidator suites).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "create_restricted_import safe_builtins create_restricted_globals relaxed", limit: 8 });
```
## Verdict
Adopt for eval/dev harnesses running semi-trusted generated code where container-per-run is too heavy; use REAL isolation (docker/e2b capsules) for hostile inputs. Keep the both-forms `__builtins__` handling.
