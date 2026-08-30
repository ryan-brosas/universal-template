<!-- capsule-v2 -->
# Optional-dependency timeout contract — how do you keep a settings field typed over a library that may not be installed?

**Source:** pydantic-ai Apache-2.0 @ `fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you make `ModelSettings.timeout` (typed `httpx.Timeout`) work when `httpx` is optional and SDKs moved to `httpx2`?

## timeout-migration-contract
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_http.py:` `DEFAULT_HTTP_TIMEOUT` (:24), conditional aliases (:31–49), `create_async_httpx2_client` (:54–65), `to_httpx2_timeout` (:68–77), `warn_if_legacy_httpx_client` (:81–103); type-side `settings.py` (:10–17); consumer `models/anthropic.py` calls `to_httpx2_timeout(model_settings.get('timeout', NOT_GIVEN))`.
**Signature:** `to_httpx2_timeout(timeout: float | LegacyTimeout | _NotGivenT) -> float | httpx2.Timeout | _NotGivenT`; module-level `LegacyTimeout = legacy_httpx.Timeout` when installed, ELSE `LegacyTimeout = httpx2.Timeout`.
**Data Shape:** `ModelSettings.timeout: int | float | Timeout` where the runtime meaning of `Timeout` degrades to plain `float` without legacy httpx ("no `Timeout` instance can reach ModelSettings, so the union member collapses onto the numeric one").

### Decisive source
```python
def to_httpx2_timeout(timeout):
    """Anything else — a plain number, or the SDK's own not-given sentinel — passes through
    unchanged, so callers can hand ModelSettings.timeout straight to a client whose HTTPX
    family no longer matches the one the setting is typed against."""
    if isinstance(timeout, LegacyTimeout):
        return httpx2.Timeout(connect=timeout.connect, read=timeout.read, write=timeout.write, pool=timeout.pool)
    return timeout
```

**Flow:** user sets `timeout=` as number or legacy `Timeout` → model layer converts legacy objects field-by-field into `httpx2.Timeout` right where the migrated SDK receives it → numbers/sentinels flow untouched → callers handing a legacy `httpx.AsyncClient` get a stacklevel-tuned deprecation warning pointing at THEIR constructor call.
**Invariant:** five rules:
1. The conversion is `isinstance`-gated on the OPTIONAL legacy class — never import `httpx` unconditionally at module top; degrade the alias, not the feature.
2. Field-by-field rebuild (`connect/read/write/pool`) — you cannot pass a legacy Timeout where httpx2 is expected, but you also must not lose any of the four buckets.
3. Pass-through for non-Timeouts is load-bearing: sentinel objects (NOT_GIVEN) and plain floats must arrive bit-identical.
4. `httpx2.Timeout` is deliberately NOT part of the accepted contract — some SDKs behind these settings still reject it (settings.py docstring :212–215).
5. Warning `stacklevel` arithmetic is a documented contract: helper adds +1 for its own frame; callers pass the value landing the warning on the user's provider-constructor call site (`_get_http_client(..., warning_stacklevel=3)`, `_create_openai_client` passes 4 because it interposes a frame — `_openai_compatible.py` comments pin both numbers).
**Probe:** `tests/test_httpx2_sdk_readiness.py` — whole-file suite asserting every provider surface accepts the settings after migration; `providers/_openai_compatible.py:_get_http_client` shows the default-client + warn-on-caller-owned fork (:16–30).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "to_httpx2_timeout create_async_httpx2_client warn_if_legacy_httpx_client DEFAULT_HTTP_TIMEOUT", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the alias-degradation + isinstance-gated rebuild + pass-through trio for ANY cross-library settings object; adapt the field list to your timeout type; omit the legacy-warning plumbing once support ends (v3 removes it). Note `DEFAULT_HTTP_TIMEOUT = 600` moved here FROM `models/__init__.py` — import site changed, value didn't.
