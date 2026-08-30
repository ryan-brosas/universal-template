<!-- capsule-v2 -->
# Interpreter state model — how do variables, functions, classes, and tools persist across agent steps?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** What exactly survives from one code action to the next, which namespaces can generated code overwrite, and where do the interpreter's own bookkeeping keys live?

## One shared dict, three tool tables
**Path/Symbol:** `src/smolagents/local_python_executor.py:evaluate_python_code` (:1583-1667), `LocalPythonExecutor` (:1688-1765, `send_variables`/`send_tools`/`__call__`), `set_value` guard (:802-805), function/class creation (`create_function` :462-526, `evaluate_class_def` :540-618).
**Signature:** `LocalPythonExecutor(additional_authorized_imports, max_print_outputs_length=None, additional_functions=None, timeout_seconds=30)`; instance fields `state`, `custom_tools`, `static_tools`.
**Data Shape:** `state` is a plain dict seeded `{"__name__":"__main__"}`; interpreter bookkeeping keys `_print_outputs` (PrintContainer) and `_operations_count` (dict) live beside user variables. Three call namespaces in strict precedence state → static_tools → custom_tools → ERRORS.

### Decisive source
```python
# :802-805 — static tools are assignment-proof:
if isinstance(target, ast.Name):
    if target.id in static_tools:
        raise InterpreterError(f"Cannot assign to name '{target.id}': doing this would erase the existing tool!")
# :1763-1765 — executor merge order (tools win over base builtins over extras):
self.static_tools = {**tools, **BASE_PYTHON_TOOLS.copy(), **self.additional_functions}
```

**Flow:** Agent start → `send_variables(self.state)` copies task inputs into sandbox state; `send_tools({**tools, **managed_agents})` installs callable tools each run (:490-492). Generated `def f(): ...` compiles to a closure-based `new_func` stored in `custom_tools` — overwritable by later code, unlike static tools; it snapshots `state.copy()` at CALL time and evaluates defaults lazily through the same evaluator. Classes build via `metaclass.__prepare__` when present (Enum support) with docstring/AnnAssign handling; methods get `__source__` so `inspect.getsource` works inside the sandbox. Because the executor reuses `self.state` across `__call__`s, functions defined in step 1 are callable in step 5 (test-pinned) — but a failed step leaves prior prints intact in `_print_outputs`.
**Invariant:** Precedence + immutability split IS the contract: state shadows everything (user variables can shadow custom_tools but never static_tools); static_tools cannot be erased or shadowed; `final_answer` is additionally wrapper-patched per call. A porter who lets generated code rebind tool names loses termination guarantees.
**Probe:** `tests/test_local_python_executor.py::test_assignment_cannot_overwrite_tool` (:77), `TestMultiStepExecutors.test_function_persistence`-style cross-call case (:2296-2313, `time.sleep(0.5)` then reuse), agents-side `test_function_persistence_across_steps` (`test_agents.py:562`). Live: one `LocalPythonExecutor`, define `add` then call it in a second execution → 5.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "static_tools custom_tools send_variables send_tools LocalPythonExecutor", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the three-table precedence and the assignment-guard on static tools. Adapt `additional_functions` placement (last = highest of the three non-tool sources). Omit the class-body metaclass emulation only if your port forbids class definitions entirely.
