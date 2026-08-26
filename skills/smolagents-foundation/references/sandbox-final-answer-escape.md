<!-- capsule-v2 -->
# FinalAnswerException escape — why does final_answer survive agent-written `except Exception`?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** When the model's generated code wraps `final_answer(...)` in a broad try/except, how does the control signal avoid being swallowed, and what must a porter replicate for termination to be guaranteed?

## BaseException-borne control flow
**Path/Symbol:** `src/smolagents/local_python_executor.py:FinalAnswerException` (:1572-1580), wrapper injection in `evaluate_python_code` (:1630-1636), catch in `_execute_code` (:1649-1654); remote twin `_patch_final_answer_with_exception` (`remote_executors.py:143-304`).
**Signature:** `class FinalAnswerException(BaseException)` with `.value`; local tool wrapped as `final_answer(*args) -> raises FinalAnswerException(previous_final_answer(*args))`.
**Data Shape:** The exception's `.value` is whatever the user's `final_answer` forward returned — locally any object; remotely a `"safe:"`/`"pickle:"`-prefixed serialized string.

### Decisive source
```python
# :1572 — the docstring IS the invariant:
class FinalAnswerException(BaseException):
    """Exception raised when final_answer is called.

    Inherits from BaseException instead of Exception to prevent being caught
    by generic `except Exception` clauses in agent-generated code.
    """
# :1633-1634 — arbitrary-arg passthrough wrapper replaces the tool in static_tools:
def final_answer(*args, **kwargs):
    raise FinalAnswerException(previous_final_answer(*args, **kwargs))
```

**Flow:** Agent code calls `final_answer(x)` → wrapper computes the real answer → raises → the interpreter's own `evaluate_try` (:1159+, catching only `Exception`) cannot intercept it → unwinds through all frames to `_execute_code`, which catches it FIRST (before the generic `except Exception`) and returns `(e.value, is_final_answer=True)` after truncating accumulated print outputs. Regression origin: GitHub issue #1905 where `try: final_answer(1) except Exception as e: final_answer(2)` wrongly returned 2.
**Invariant:** Termination of the code-action loop depends on this signal being uncatchable by *generated* code. Porting it as a subclass of `Exception` reintroduces the #1905 bug. Note also `ReturnException`/`BreakException`/`ContinueException` (:266-277) are plain `Exception`s on purpose — those SHOULD be catchable by generated code because they emulate Python statement semantics; do not "unify" them with FinalAnswerException.
**Probe:** `tests/test_local_python_executor.py::test_final_answer_not_caught_by_except_exception` (:1406-1422, asserts result==1 not 2) + `test_final_answer_accepts_kwarg_answer` (:1401, kwargs pass through the wrapper). Live: run both snippets through `evaluate_python_code`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "FinalAnswerException BaseException final_answer", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt BaseException-derived control signals for anything that must terminate agent code. Adapt the payload shape per transport (remote executors serialize `.value` with prefix tagging — see `smolagents-remote-final-answer-patching`). Omit the local double-execution subtlety at your peril: the wrapper runs the real forward BEFORE raising, so side effects happen exactly once.
