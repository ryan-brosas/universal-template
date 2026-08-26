<!-- capsule-v2 -->
# Runtime settings overlay — DB-backed admin config with env fallback, 15s cache, and paranoid normalization

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** How should runtime-editable config (AI policy, weights, provider lists) resolve across DB rows and env vars without letting an admin typo take the service down?

## Defaults-first builders over a TTL-cached settings map
**Path/Symbol:** `backend/app/services/runtime_settings.py` whole (872L): `_load_runtime_settings` :288–318 (double-checked 15s TTL cache + asyncio.Lock), `_pick_string/_pick_int/_pick_float/_pick_bool` :320–362, `_build_ai_usage_policy_config` :723–830, `_build_diagnostic_rule_config` :478–500, `_build_llm_provider_config` :415–455.
**Signature:** `get_ai_usage_policy_config(force_refresh: bool = False) -> dict[str, Any]` (+ five sibling getters); `POSTGRES_INTEGER_MAX = 2_147_483_647`.
**Data Shape:** Raw values: `{setting_key: json|encrypted-dict}`; built configs are flat dicts with VALIDATED enums (`VALID_AI_ACCESS_MODES`, `VALID_LLM_PROVIDER_STRATEGIES`) and clamped numerics.

### Decisive source
```python
access_mode = _pick_string(raw.get("access_mode"), defaults["access_mode"])
if access_mode not in VALID_AI_ACCESS_MODES:
    access_mode = defaults["access_mode"]                 # unknown enum ⇒ default
if access_mode in {"daily_quota", "quota_with_byok"}:
    access_mode = "lifetime_quota_with_byok"              # legacy modes silently migrate forward
...
"daily_token_limit": min(POSTGRES_INTEGER_MAX, max(0, _pick_int(...))),   # clamp to column range
```
```python
async with _cache_lock:                    # inside-lock re-check = single DB read per TTL window
    now = time.monotonic()
    if _settings_cache and now < _cache_expires_at:
        return dict(_settings_cache)
```
Deprecated daily-quota modes are FORCED into the lifetime model; `byok_transport_mode` accepts only the two known strings, everything else ⇒ `proxy_transient`.

**Flow:** every getter → TTL cache (monotonic clock, lock-guarded double-check) → decrypt sensitive values (`decrypt_setting_value`) → builder merges DEFAULTS ⊂ raw with type-picking helpers → enum validation falls back to default on garbage → numeric clamps to [0, PG_INT_MAX] → legacy value migration. Admin writes go through `normalize_*_payload` twins so stored JSON is always in validated shape.
**Invariant:** A corrupt or hostile settings row can only degrade to defaults — never raise, never produce out-of-range numbers, never activate an unvalidated enum. Cache invalidation is explicit (`invalidate_runtime_settings_cache`) on admin write.
**Probe:** `backend/tests/test_ai_quota_rules.py::test_policy_normalization_clamps_numbers_and_sanitizes_guidance` (negative grants, javascript: URLs in guidance rejected).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "_build_ai_usage_policy_config", limit: 5 });
// verified line-exact: runtime_settings.py :723–830
```

## Verdict
Adopt the builder+clamp+enum-default pattern for ANY admin-editable runtime config; adapt setting keys/TTL; omit the homepage-release machinery if you have no static-site publishing. Direct tests green under real runner.
