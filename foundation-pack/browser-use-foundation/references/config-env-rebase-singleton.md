<!-- capsule-v2 -->
# Env-rebase config singleton — how does config stay LIVE to environment changes in a long-running agent process?

**Source:** browser-use MIT `main@3c989dc0`; Codebase Memory `browser-use`. **Question:** when your library reads config from env vars, how do you guarantee a value exported AFTER import time is still honored hours later — without re-plumbing every call site?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/config.py` — `Config.__getattr__` (:370-403), `OldConfig` property ladder (:47-188), module singleton `CONFIG = Config()` (:514).
**Signature:** `class Config:` with ONLY `__init__(self)` storing `_dirs_created` + `def __getattr__(self, name) -> Any`; every attribute access constructs a FRESH `OldConfig()` / `FlatEnvConfig()` and delegates.

### Decisive source
```python
def __getattr__(self, name: str) -> Any:
    """Dynamically proxy all attributes to fresh instances.

    This ensures env vars are re-read on every access.
    """
    if name.startswith('_'):
        raise AttributeError(...)
    old_config = OldConfig()          # NEW instance EVERY access
    if hasattr(old_config, name):
        return getattr(old_config, name)   # properties re-run os.getenv()
    env_config = FlatEnvConfig()      # then pydantic-settings fallback
    if hasattr(env_config, name):
        return getattr(env_config, name)
    ...
# OldConfig.ANONYMIZED_TELEMETRY (:59):
return os.getenv('ANONYMIZED_TELEMETRY', 'true').lower()[:1] in 'ty1'
```

**Flow:** `CONFIG.<ATTR>` → dunder-lookup misses → `__getattr__` → fresh `OldConfig()` whose @property re-executes `os.getenv` → value reflects CURRENT environ → unknown names fall through to a fresh `FlatEnvConfig()` (pydantic-settings, also re-reads env/.env) → still unknown ⇒ AttributeError. Underscore names short-circuit to AttributeError so private machinery never proxies.
**Invariant:** NEVER cache a resolved config value across calls — the whole design point is that `os.getenv` runs on every access; a porter who memoizes breaks late-exported env vars (the MCP-server use case where env arrives after launch). Two parse traps: (1) bool fields use `.lower()[:1] in 'ty1'`, so **empty string parses TRUE** (`'' in 'ty1'` is True because `in` is substring!) while `'0'/'f'/'n'` parse FALSE — set `ANONYMIZED_TELEMETRY=` expecting False and you silently ENABLE telemetry; (2) `BROWSER_USE_CLOUD_SYNC` defaults to `str(self.ANONYMIZED_TELEMETRY)` — cloud sync inherits the telemetry flag unless explicitly overridden.
**Probe:** EXECUTED behavioral probe at pin `3c989dc0` (no upstream unit test for this class): set `ANONYMIZED_TELEMETRY=''` → `OldConfig().ANONYMIZED_TELEMETRY is True`; set `'0'` → False. Migration behavior pinned by round-trip probes below.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "Config __getattr__ OldConfig FlatEnvConfig CONFIG singleton", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fresh-instance-per-access proxy pattern for any env-driven config read post-import; adopt the underscore short-circuit. Adapt the `'ty1'` parser to a strict truthy-set (`{'1','t','y','true','yes'}`) — the substring trap is a bug-shaped idiom, not a feature. Omit the 20+ per-provider API-key property boilerplate (data, not contract). Caveat: no direct upstream test pins this class; probes were executed against the pin by this lane.
