<!-- capsule-v2 -->
# Windows DLL diagnosis middleware — naming the missing VC++ runtime instead of a bare import error

**Source:** linkedin-mcp-server Apache-2.0 `main@cfcd9c9a`; Codebase Memory `linkedin-mcp-server`. **Question:** When a third-party C extension fails to load for a missing runtime DLL, how do you translate the failure into an actionable error without misclassifying it?

## greenlet_runtime.explain_a_missing_runtime()
**Path/Symbol:** `linkedin_mcp_server/greenlet_runtime.py:explain_a_missing_runtime()` (:150-end); runs at package import.
**Signature:** `explain_a_missing_runtime() -> None` — non-Windows or healthy import = no-op; `ImportError` starting with `"DLL load failed"` AND loader refusing `msvcp140.dll` ⇒ raise `VisualCPPRuntimeUnavailableError(_explain(...))`.
**Data Shape:** Two narrowing checks, never proving: prefix match on CPython's exact dynload message (`dynload_win.c` writes it for every failed `LoadLibraryExW`, so it also covers corrupt .pyd / arch mismatch); then `ctypes.CDLL("msvcp140.dll")` probe.

### Decisive source
```python
# Nothing here consults the installed greenlet version... Linking is a
# property of the built artifact, not of the number: 3.2.5 publishes no
# Windows wheel at all ... while 3.5.5 is static again at a number above
# every broken one. A version predicate is wrong in both directions and
# fails in the expensive one, withholding the explanation from someone
# whose problem this is.
#
# The search orders differ slightly: CPython loads an extension with
# LOAD_LIBRARY_SEARCH_DEFAULT_DIRS | LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR while
# ctypes.CDLL given a bare name uses the first flag alone, so a
# MSVCP140.dll sitting beside _greenlet.pyd and nowhere else is found by
# the real import and missed here [— hence narrow, never prove].
```
Message ordered for truncating clients: fix FIRST (`Install the Microsoft Visual C++ Redistributable` + URL), workaround second (`uvx --with "greenlet<=3.3.0"`), evidence last (loader line + installed version read via importlib.metadata with all failures swallowed — inside an already-failing import, a broken METADATA must not mask the real error).

**Flow:** package import → probe greenlet import → if loader-shaped failure → probe runtime DLL → translate or re-raise untouched.
**Invariant:** Version numbers don't decide binary-compat questions — build artifacts do; diagnosis narrows but never claims proof; remediation text leads the message because clients truncate. The check lives at package import because that's the only place both entry paths pass before reaching the dependency.
**Probe:** `tests/test_greenlet_runtime.py` pins translation vs re-raise branches.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "explain_a_missing_runtime VisualCPPRuntimeUnavailableError greenlet", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the narrow-checks-plus-actionable-message pattern for any native-dependency failure surface. Adapt DLL names/platforms. Omit greenlet history.
