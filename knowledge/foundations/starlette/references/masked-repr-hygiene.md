<!-- capsule-v2 -->
# Masked repr hygiene — how do Secret and URL keep credentials out of logs and tracebacks?

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `starlette`. **Question:** Where must masking happen so a signing key or basic-auth password never lands in an exception message or log line?

## Secret full-mask + URL.__repr__ component mask
**Path/Symbol:** `starlette/datastructures.py:Secret` (:205-222); `:URL.__repr__` (:168-172). Consumer: `starlette/middleware/sessions.py:SessionMiddleware.__init__` (:29).
**Signature:** `Secret(value: str)`; `URL.__repr__(self) -> str`.
**Data Shape:** Secret wraps the raw string in `_value` with three delegating dunders: `__repr__` ALWAYS prints `Secret('**********')`, `__str__` reveals, `__bool__` delegates truthiness (so empty secrets are falsy without unmasking). URL keeps the true URL in `_url`; only the repr re-renders with the password component replaced.

### Decisive source
```python
def __repr__(self) -> str:
    class_name = self.__class__.__name__
    return f"{class_name}('**********')"
def __str__(self) -> str:
    return self._value
def __bool__(self) -> bool:
    return bool(self._value)
```
```python
def __repr__(self) -> str:
    url = str(self)
    if self.password:
        url = str(self.replace(password="********"))
    return f"{self.__class__.__name__}({repr(url)})"
```

**Flow:** SessionMiddleware accepts `secret_key: str | Secret` but immediately narrows it at construction: `itsdangerous.TimestampSigner(str(secret_key))` — the cast-to-str happens at exactly ONE internal point; every accidental `print(config.SECRET)` / traceback frame / f-string that uses repr instead of str shows stars. URL masking is render-time only: `str(url)` and `.components` still expose the real password to code that deliberately asks.
**Invariant:** masking lives in `__repr__`, not in storage — because Python's default logging/traceback/REPL formatting calls repr on embedded objects. A port that masks by storing a redacted copy breaks actual use; one that overrides only `__str__` still leaks through tracebacks. `URL.__eq__` compares `str(self) == str(other)`, so masked reprs never affect equality.
**Probe:** `tests/test_datastructures.py::test_hidden_password` (:89-97 — username stays visible, password becomes `********` in repr); consumer pinned by `tests/middleware/test_session.py` (signer constructed from str(secret_key)).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "starlette", namePattern: "Secret", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "starlette", query: "repr password mask secret", limit: 10 });
```

## Verdict
Adopt repr-side masking for credential-carrying value objects and the str()-at-use discipline for consumers. Adapt the mask literal per host convention. Omit encrypting the stored value — the contract is presentation-layer only, and deliberate str()/components access remains the escape hatch. Both paths coverage-clean at pin.
