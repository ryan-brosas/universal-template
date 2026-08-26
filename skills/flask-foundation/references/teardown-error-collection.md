<!-- capsule-v2 -->
# Teardown error collection — how do ALL teardown callbacks run even when they raise, and what surfaces?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** What replaces "stop at first teardown error", and how are the three teardown phases ordered?

## _CollectErrors + raise_any
**Path/Symbol:** `src/flask/helpers.py:_CollectErrors` (654–682); driven by `src/flask/ctx.py:AppContext.pop` (486–504) and `src/flask/app.py:do_teardown_request` (1423–1454) / `.do_teardown_appcontext` (1456–1482).
**Signature:** `_CollectErrors.__exit__` swallows+records; `.raise_any(message)` re-raises as group.
**Data Shape:** request phase wraps each callback + signal + `request.close()`; app phase wraps app-teardown funcs + signal; pop wraps both phases.

### Decisive source
```python
class _CollectErrors:
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_val is not None:
            self.errors.append(exc_val)
        return True                       # swallow; keep going
    def raise_any(self, message):
        if self.errors:
            if sys.version_info >= (3, 11):
                raise BaseExceptionGroup(message, self.errors)
            raise self.errors[0]          # <3.11: first error only

# AppContext.pop ordering:
if self._request is not None:
    with collect_errors: self.app.do_teardown_request(self, exc)
    with collect_errors: self._request.close()
with collect_errors: self.app.do_teardown_appcontext(self, exc)
_cv_app.reset(self._cv_token)
...
collect_errors.raise_any("Errors during context teardown")
```

**Flow:** pop → request teardown funcs over blueprint chain innermost→app REVERSED (each isolated) + request_tearing_down signal → close request → appcontext teardown funcs reversed + signal → reset ContextVar → popped signal → ONE grouped raise containing any errors.
**Invariant:** every registered callback runs regardless of earlier failures; ContextVar is still reset before the group raises; <3.11 loses all-but-first error (documented degradation).
**Probe:** `grep -Fc 'raise BaseExceptionGroup(message, self.errors)' src/flask/helpers.py` = 1; `grep -Fc 'collect_errors.raise_any("Errors during context teardown")' src/flask/ctx.py` = 1; test `tests/test_appctx.py::test_robust_teardown` (:216) asserts nested ExceptionGroups ("request teardown" ×2 inside "context teardown").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "_CollectErrors teardown raise errors", limit: 6 });
```

## Verdict
Adopt collect-then-group so cleanup is total and observable. Adapt message strings. Omit the 3.10 fallback only if you require ≥3.11.
