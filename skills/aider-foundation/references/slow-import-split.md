<!-- capsule-v2 -->
# Slow-import split — installs.json keyed first-run gate choosing sync-fail vs background thread, plus the LazyLiteLLM attribute proxy that defers the 1.5 s litellm import

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How does a CLI cut seconds off every launch when its heaviest imports (litellm/httpx/numpy/networkx) are needed only later, without hiding a broken install — and how does the single heaviest import hide behind an attribute proxy?

## First run for this (version, executable) pair fails loudly; every later run defers to a daemon thread
**Path/Symbol:** `aider/main.py`: `is_first_run_of_new_version(io, verbose=False)` (:1183), `check_and_load_imports(io, is_first_run, verbose=False)` (:1226), `load_slow_imports(swallow=True)` (:1256); key = `str((__version__, sys.executable))` against `~/.aider/installs.json`.
**Signature:** `load_slow_imports(swallow: bool = True)` — raises only when `swallow=False`; the flag is set at exactly one call site (:1234).
**Data Shape:** installs.json is a flat dict of `"('v0.82.0', '/usr/bin/python3')": true`; any read/write error ⇒ treat as first run (fail-safe toward the loud path).

### Decisive source
```python
is_first_run = str(key) not in installs
if is_first_run:
    installs[str(key)] = True
    ...write...
    return True
...
if is_first_run:
    try:
        load_slow_imports(swallow=False)
    except Exception as err:
        io.tool_error(str(err))
        io.tool_output("Error loading required imports. Did you install aider properly?")
        io.offer_url(urls.install_properly, ...)
        sys.exit(1)
else:
    thread = threading.Thread(target=load_slow_imports)
    thread.daemon = True
    thread.start()
```

**Flow:** on first-ever run of this version+interpreter combination the heavy modules import synchronously so a broken environment produces an actionable error + docs URL + exit 1; afterwards the same import work happens in a daemon thread that dies silently with the process. `.dev` versions never count as first runs (:1189).
**Invariant:** the failure-visibility contract is version-scoped — a user sees install errors once per upgrade, not on every launch; the marker is written BEFORE the sync import attempt, so a crash still records "seen" and subsequent launches take the quiet background path.
**Probe:** deterministic: `grep -c 'load_slow_imports' aider/main.py` → 3 (def :1256, sync call :1234, thread target :1246). Direct tests: none upstream for these helpers (source-pinned; test_main.py covers surrounding flows).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "load_slow_imports", limit: 3 });
// rank-1: aider.aider.main.load_slow_imports aider/main.py 1256-1269
```

## Second half of the slow-import story: the LazyLiteLLM attribute proxy
**Path/Symbol:** `aider/llm.py` (whole file, 47 L): `LazyLiteLLM.__getattr__` (:24-28), `LazyLiteLLM._load_litellm` (:30-42), module singleton `litellm = LazyLiteLLM()` (:45).
**Signature:** `__getattr__(self, name)` forwards any attribute through a one-time `importlib.import_module("litellm")`; the name `_lazy_module` short-circuits to `super()` to avoid recursion.
**Data Shape:** `_lazy_module: module | None` — the None sentinel doubles as the process-wide "is litellm really loaded?" predicate.

### Decisive source
```python
class LazyLiteLLM:
    _lazy_module = None

    def __getattr__(self, name):
        if name == "_lazy_module":
            return super()
        self._load_litellm()
        return getattr(self._lazy_module, name)

    def _load_litellm(self):
        if self._lazy_module is not None:
            return
        self._lazy_module = importlib.import_module("litellm")   # ~1.5s, deferred
        self._lazy_module.suppress_debug_info = True
        self._lazy_module.set_verbose = False
        self._lazy_module.drop_params = True
        self._lazy_module._logging._disable_debugging()
```

**Flow:** importing `aider.llm` is nearly free: it only seeds env vars (`OR_SITE_URL`, `OR_APP_NAME`, `LITELLM_MODE=PRODUCTION`), filters pydantic UserWarnings, and instantiates the proxy. The first attribute touch (`litellm.completion(...)`) pays the import once, then hardens the module (suppress debug info, disable verbose/logging, drop unsupported params). Downstream contract: `models.py get_model_info` gates heavy work on `litellm._lazy_module or not cached_info` — truthiness of the sentinel answers "loaded?" without triggering it.
**Invariant:** the proxy must never expose its own internals as litellm attributes (the `_lazy_module` guard prevents `getattr(litellm, "_lazy_module")` from recursing), and hardening must run exactly once at load time, not per call.
**Probe:** deterministic: whole-file read of aider/llm.py confirms 47 L total and the four hardening assignments at :39-42; DSH grep `_lazy_module` in aider/coders/base_coder.py + aider/models.py shows consumers reading the sentinel rather than importing litellm directly.

## Verdict
Adopt the installs-ledger + dual-path import pattern verbatim for plugin-heavy CLIs; adapt the key tuple (add OS/arch if wheels differ). Porters who skip the swallow=False distinction ship CLIs where a broken install loops forever with no error — that asymmetry IS the capsule.
