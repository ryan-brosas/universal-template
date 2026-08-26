<!-- capsule-v2 -->
# Error-taxonomy vocabulary — what exception types exist, which are actually raised, and why does the message carry the original error?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** How should a multi-agent orchestrator's exception hierarchy be shaped when a catch-and-continue funnel, not per-type handling, consumes the exceptions?

## Five-class CustomException family with `original_error` attachment; two of five classes never raised
**Path/Symbol:** `core/utils/custom_exceptions.py` (`:1-22`, whole file); raise sites all in `core/orchestrator.py` (`:371` PlannerError, `:398`/:496 CustomException, `:519` SSAnalysisError).
**Signature:** `class CustomException(Exception): def __init__(self, message, original_error=None)`.
**Data Shape:** Fields `self.message` + `self.original_error` (the caught exception object itself), passed to `super().__init__(self.message)`. Subclasses: PlannerError, BrowserNavigationError, SSAnalysisError, CritiqueError — all `pass` bodies.

### Decisive source
```python
# custom_exceptions.py :2-7 — the whole contract
class CustomException(Exception):
    """Base exception class for orchestrator-specific errors"""
    def __init__(self, message, original_error=None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)

# orchestrator.py :517-519 — wrap-with-context at the failure site
error_msg = f"SS Analysis failed: {str(e)}"
logfire.error(error_msg, exc_info=True)
...
raise SSAnalysisError(error_msg, original_error=e)
```
**Flow:** every raise site formats a human-readable `error_msg` FIRST (that string is simultaneously logged, shown to the user via notify_user, and carried as the exception message), then raises the typed wrapper carrying the live exception object as `original_error`. The step funnel (:606) converts any of them into notify+retry. **Dead twins:** `BrowserNavigationError` and `CritiqueError` have ZERO raise sites repo-wide (grep-verified) — navigation failures ride `browser_error` into the critique prompt instead, and critique failures re-raise raw (:578). A porter who wires handlers per class will wait forever on those two.
**Invariant:** The typed exception is an ENVELOPE for user-facing text + original context, not a control-flow discriminator — nothing in the codebase does `except PlannerError:`; classification happens earlier via string-matching (`context_length_exceeded`) and structurally via where the error was raised. Keep `original_error` so funnel logs keep the stack story; keep messages user-displayable since they go straight to notify_user.
**Probe:** `grep -c "class.*CustomException" core/utils/custom_exceptions.py` → `5` (base + four subclasses); `grep -rn "PlannerError\|SSAnalysisError" core/orchestrator.py | grep -c "raise"` → `2`; `grep -rn "BrowserNavigationError(" core/ --include='*.py' | grep -v custom_exceptions.py | wc -l` → `0`; same for `CritiqueError(` → `0`; `grep -n "original_error=e" core/orchestrator.py` → `373, 398, 496, 519`. Coverage caveat: no upstream tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "CustomException PlannerError SSAnalysisError original_error", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt: envelope pattern (user-facing message + original_error attachment) and raise-site formatting. Omit: BrowserNavigationError/CritiqueError as dead twins unless your port adds real navigation/critique handlers — record them as reserved vocabulary, not working code. Coverage caveat: no upstream tests; probes line-pinned at pin `71daa28`.
