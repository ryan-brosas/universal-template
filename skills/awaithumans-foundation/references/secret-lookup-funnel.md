<!-- capsule-v2 -->
# Secret Lookup Funnel — one Settings.get_secret instead of scattered os.environ reads

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** Why must verifier API keys be read through Settings even when their env-var name arrives at runtime in task config?

## Declared-field first, os.environ fallback for undeclared names
**Path/Symbol:** `packages/python/awaithumans/server/core/config.py` — `Settings.get_secret` (:100-130).
**Signature:** `get_secret(self, env_name: str) -> str | None` — None when unset so CALLERS raise their own typed errors (e.g. VerifierAPIKeyMissingError).
**Data Shape:** lookup order: case-insensitive attribute match against declared pydantic-settings fields (`.upper()` then getattr) → raw `os.environ.get(env_name)`.

### Decisive source
```python
# 1. CLAUDE.md §6 forbids raw os.environ.get(...) outside core/config.py.
#    Concentrating reads gives one place to add scrubbing / audit / .env
#    normalisation later without chasing call sites.
# 2. pydantic-settings picks up declared fields automatically — a bare
#    os.environ.get() would MISS .env loading on those. We try the model
#    attribute first, then fall back for fields the operator added themselves
#    via VerifierConfig.api_key_env without us pre-declaring a Settings field.
attr = getattr(self, env_name.upper(), None)
if isinstance(attr, str) and attr:
    return attr
return _os.environ.get(env_name) or None
```

**Flow:** verifier provider needs key named by `VerifierConfig.api_key_env` (operator-chosen, NOT pre-declared) → call settings.get_secret(name) → declared-field hit covers `.env` files; fallback covers ad-hoc vars → empty string treated as unset (the `and attr` truthiness) → caller raises typed error on None.
**Invariant:** the funnel is the ONLY sanctioned os.environ reader outside config.py — porters who keep raw environ reads lose `.env` support AND the future single point for scrubbing/audit.
**Probe:** `packages/python/tests/core/test_settings_get_secret.py` (`test_returns_value_from_settings_field`:27, `test_falls_back_to_os_environ_for_undeclared_var`:37, `test_empty_string_treated_as_unset`:52, `test_case_insensitive_match_on_settings_field`:60).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "get_secret Settings undeclared env var verifier api key", limit: 4 });
```
Live rank-1/2 resolve the direct tests; the method itself sits in config.py :100-130.

## Verdict
Adopt the funnel + two-reason rationale verbatim (it's a governance contract as much as code); adapt field-matching case rules to your settings library; omit the environ fallback only if you can force every operator var to be declared.
