<!-- capsule-v2 -->
# Pristine-defaults snapshot via loader swap + reload — how do you show users the untouched defaults when overrides are applied at import time?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550f8aa80027621cfc17a30fceba05705f84`; Codebase Memory `Auto_job_applier_linkedIn`. **Question:** config modules apply a JSON overlay as they are imported — how can a UI display "default overlaid with current saved values" without lying about either layer?

## Capture pristine defaults by temporarily disabling the override loader and re-importing
**Path/Symbol:** `app.py:_load_defaults` (:55–90), `DEFAULTS` (:90), `_effective_config` (:96–110); overlay kernel it neutralizes: `config/_overrides.py:apply` (:39–55, called at the tail of every `config/*.py`).
**Signature:** `_load_defaults() -> {config_module: {key: default_value}}`; `_effective_config() -> {module: {key: value}}`.
**Data Shape:** DEFAULTS = deep snapshot taken once at panel startup; effective view = `copy.deepcopy(DEFAULTS)` re-overlaid from a FRESH disk read of user_config.json on every GET (only keys present in config_schema participate).

### Decisive source
```python
original_loader = _overrides.load_user_config
_overrides.load_user_config = lambda: {}        # pretend no user JSON exists
try:
    import config.secrets as _secrets; ...      # import all five config modules
    for module in modules.values(): importlib.reload(module)   # rerun their bodies WITHOUT overrides
    for field in config_schema.iter_fields():   # harvest exactly the schema-declared keys
        defaults.setdefault(field["config_module"], {})[field["key"]] = getattr(module, field["key"], None)
    return defaults
finally:
    _overrides.load_user_config = original_loader   # restore the real overlay
```

**Flow:** startup → stub the loader → import/reload each config module so its module-body executes with an empty overlay (pristine Python defaults) → copy schema-declared keys into DEFAULTS → restore loader. Every later GET rebuilds effective = deepcopy(DEFAULTS) + fresh user_config.json values.
**Invariant:** the stub is ALWAYS restored (`finally`); only schema-declared keys are harvested or overlaid, so unknown JSON names can never leak into either view; the effective read re-reads disk every call (external edits to user_config.json show up without restart).
**Probe:** `tests/test_app_integration.py::test_config_save_coerces_and_roundtrips` — POST {"secrets": {"use_AI": "true"}} coerces to real bool on disk AND "GET reflects the saved value" over defaults (executed this pass: suite green). Reload side effects make this test-only-safe because config modules are pure data plus the apply call.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "_load_defaults _effective_config defaults reload", limit: 8 });
// → app._load_defaults app.py :55-87 · app._effective_config :96-110
```

## Verdict
Adopt the loader-swap+reload snapshot for import-time-override architectures, deepcopy-per-read effective views, and schema-keyed harvesting; adapt module lists per host; omit reload tricks outside startup (re-running module bodies with real side effects would double-apply). Works because this repo's config modules are declarative — pair with config-override-noop-layer for the overlay kernel itself.
