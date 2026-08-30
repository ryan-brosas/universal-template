<!-- capsule-v2 -->
# LiteLLM exception taxonomy — closed-world retry table with strict sync check and string-sniffed sub-cases

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How does an agent decide which provider errors are transient (retry with backoff) versus fatal (tell the user now), when the underlying SDK's exception surface changes across versions?

## One declarative table; lazy load with strict drift check; per-instance overrides via str(ex) sniffing
**Path/Symbol:** `aider/exceptions.py`: `ExInfo` dataclass (:7, fields name/retry/description), `EXCEPTIONS` list (:13-57, 24 entries), `LiteLLMExceptions` class (:60), `_load(strict=False)` (:67), `get_ex_info(ex)` (:85).
**Signature:** `_load()` maps every listed name to the LIVE litellm attribute (`self.exceptions[ex] = self.exception_info[var]`) so catching works by identity; `get_ex_info` returns `ExInfo(None, None, None)` for unknown classes — callers must treat falsy `retry` as "no info".
**Data Shape:** retry=True for connection/rate-limit/server families; retry=False for AuthenticationError, BadRequestError, ContextWindowExceededError (special-cased in base_coder), NotFoundError, PermissionDeniedError, ImageFetchError.

### Decisive source
```python
def _load(self, strict=False):
    import litellm
    for var in dir(litellm):
        # Filter by BaseException because instances of non-exception classes
        # cannot be caught. `litellm.ErrorEventError` is an example of a
        # regular class which just happens to end with `Error`.
        if var.endswith("Error") and issubclass(getattr(litellm, var), BaseException):
            if var not in self.exception_info:
                raise ValueError(f"{var} is in litellm but not in aider's exceptions list")
...
def get_ex_info(self, ex):
    if ex.__class__ is litellm.APIConnectionError:
        if "boto3" in str(ex):
            return ExInfo("APIConnectionError", False, "You need to: pip install boto3")
        ...
    if ex.__class__ is litellm.APIError:
        err_str = str(ex).lower()
        if "insufficient credits" in err_str and '"code":402' in err_str:
            return ExInfo("APIError", False, "Insufficient credits ...")
```

**Flow:** instantiation lazily imports litellm and binds the table; `strict=True` (used by tests AND safe to call by ops tooling) fails loudly on any drift between the SDK surface and the table; at error time base_coder looks up the instance's exact class first, then applies the boto3-missing / OpenRouter-down / insufficient-credits string refinements that REVERSE the default retry verdict.
**Invariant:** unknown exceptions are never retried by this layer (empty ExInfo); the closed-world check converts silent catch-gaps into a startup/test-time ValueError.
**Probe:** EXECUTED this run under repo venv: `LiteLLMExceptions()._load(strict=True)` → OK binding **23** live litellm exception classes (24 table rows minus ContextWindowExceededError, which is not exported as a class by this litellm version — the strict check only validates names PRESENT in dir(litellm)). Deterministic: `grep -c 'ExInfo(' aider/exceptions.py` → 27 (24 EXCEPTIONS rows + 3 constructions inside get_ex_info). Direct test: `tests/basic/test_sendchat.py::test_litellm_exceptions` (:18) runs the same strict load.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "LiteLLMExceptions", limit: 3 });
// rank-1: aider.aider.exceptions.LiteLLMExceptions.__init__ aider/exceptions.py 64-65
```

## Verdict
Adopt the closed-world table + strict sync probe pattern for any LLM harness wrapping a fast-moving SDK; adapt the three string-sniffed overrides to your providers. Porters who copy only the retry booleans lose the point: the VALUE is failing loudly when the SDK grows a new exception your table doesn't classify.
