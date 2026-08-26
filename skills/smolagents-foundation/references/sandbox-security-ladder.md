<!-- capsule-v2 -->
# Sandbox security ladder — how does the local executor stop agent-written code from reaching dangerous Python?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** When porting a restricted Python evaluator, which layers must exist and in what order, so that imports, builtins, attributes, and even *return values* of allowed calls cannot smuggle out capabilities?

## Layered denial ladder
**Path/Symbol:** `src/smolagents/local_python_executor.py:evaluate_call` (:825-918), `check_safer_result` (:156-182), `safer_func` (:211-237), `ALLOWED_DUNDER_METHODS` (:61).
**Signature:** `check_safer_result(result, static_tools=None, authorized_imports=None)`; `safer_eval` wraps `evaluate_ast`, `safer_func(func, static_tools=BASE_PYTHON_TOOLS, authorized_imports=BASE_BUILTIN_MODULES)` wraps every resolved static tool.
**Data Shape:** Denials raise `InterpreterError(ValueError)` with a stable message vocabulary: `"Import of X is not allowed..."`, `"Forbidden access to module: X"`, `"Forbidden access to function: X"`, `"Forbidden access to dunder attribute: X"`, `"Forbidden call to dunder function: X"`, `"Invoking a builtin function that has not been explicitly added as a tool is not allowed"`.

### Decisive source
```python
# Name resolution refuses anything not explicitly provided (evaluate_call :847-860):
elif func_name in static_tools:   func = static_tools[func_name]
elif func_name in custom_tools:   func = custom_tools[func_name]
elif func_name in ERRORS:         func = ERRORS[func_name]     # exception classes ARE callable
else: raise InterpreterError(f"Forbidden function evaluation: '{call.func.id}' is not among the explicitly allowed tools...")
# ...and every static-tool RETURN VALUE is re-screened (safer_func :232-235):
result = func(*args, **kwargs)
check_safer_result(result, static_tools, authorized_imports)
```

**Flow:** (1) `import` statements pass `check_import_authorized` (see `smolagents-import-authorization-tree`) else deny; (2) bare-name calls resolve ONLY through state → static_tools → custom_tools → ERRORS (builtins like `eval` are invisible because they are never in any table); (3) builtin objects reached another way still fail `inspect.getmodule(func)==builtins and isbuiltin and func not in static_tools.values()` (:906-909); (4) dunder attribute reads denied at `ast.Attribute` unless name ∈ {`__init__`,`__str__`,`__repr__`} (:383-393, :61); (5) dunder *calls* denied unless in static_tools or ALLOWED_DUNDER_METHODS (:910-917); (6) `safer_func` re-checks each tool call's RESULT so e.g. an authorized `os` import still blocks `os.popen` access (:174-182) — pinned parametrized across ALL of DANGEROUS_FUNCTIONS; (7) module objects returned anywhere are checked against the authorization tree, including modules hidden in dicts via `__spec__` (:168-173) — kills `sys.modules["os"]`.
**Invariant:** The blocklists (DANGEROUS_MODULES/DANGEROUS_FUNCTIONS) are only backstops; the load-bearing property is *allowlist-only resolution*: nothing is callable that was not explicitly injected, and no call's return value escapes unchecked. Porters who keep only the blocklists recreate CVEs.
**Probe:** `tests/test_local_python_executor.py::TestLocalPythonExecutorSecurity` (:2440+) — parametrized matrix incl. `test_vulnerability_via_sys` expecting `Forbidden access to module: os` after `["sys"]` authorization. Live: `python3 -c` with `LocalPythonExecutor(["os"])` running `import os; os.popen` → `InterpreterError: Forbidden access to function: popen`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "check_safer_result safer_func forbidden", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the layered ladder and the stable error-message vocabulary (the agent's retry prompt depends on reading these messages). Adapt the DANGEROUS_* lists per host runtime. Omit nothing from layer (6): return-value screening is the non-obvious half and the reason `authorized_imports=["os"]` is still survivable. Coverage caveat: this is a restriction layer, NOT a security sandbox — `LocalPythonExecutor`'s own docstring (:1692-1694) says use remote executors for untrusted code.
