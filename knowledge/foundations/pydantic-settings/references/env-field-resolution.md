<!-- capsule-v2 -->
# Env name ladder — which environment variable names map to a field, and in what precedence?

**Source:** pydantic-settings MIT `main@d26fc0c3944fe68cf169f86386988bb83e3df2d8`; Codebase Memory `pydantic-settings`. **Question:** Given `validation_alias` (AliasChoices/AliasPath), `populate_by_name`, `env_prefix`, and `case_sensitive`, exactly which env var is read for a field and what key does the value land under?

## Connected graph-selected seam
**Path/Symbol:** `pydantic_settings/sources/base.py:PydanticBaseEnvSettingsSource._extract_field_info` (within 395-629); `providers/env.py:EnvSettingsSource.get_field_value` (96-117), `_load_env_vars` (86-94).
**Signature:** `def _extract_field_info(self, field: FieldInfo, field_name: str) -> list[tuple[str, str, bool]]` — triples of `(field_key, env_name, value_is_complex)`.
**Data Shape:** env lookup map pre-normalized by `parse_env_vars` (`_get_env_var_key` lowercases when not case-sensitive; `_parse_env_none_str` tags the configured none-string as `EnvNoneType`; empty strings dropped under `env_ignore_empty`).

### Decisive source
```python
for field_key, env_name, value_is_complex in self._extract_field_info(field, field_name):  # noqa: B007
    env_val = self.env_vars.get(env_name)
    if env_val is not None:
        break
```
and inside `_extract_field_info`: alias entries are tried first (`env_prefix` applied to them only when
`env_prefix_target in ('alias', 'all')`), then the bare field-name entry is appended only when there is no
validation alias or `populate_by_name`/`validate_by_name` is set (`env_prefix_target in ('variable', 'all')`);
complex-union detection marks that entry `value_is_complex=True`.

**Flow:** Build candidate triples once per field → scan in order → first non-None env hit wins → return `(value, field_key_of_winner, complex_flag)`; `_get_resolved_field_value` then normalizes the returned key back to the *preferred* alias so all sources agree on one key per field. On Windows, real `os.environ` is case-insensitive at the OS level, so `case_sensitive=True` is downgraded to `False` for environ loads only (`_environ_is_case_insensitive`, issue #295) — `.env` files keep their own case handling.
**Invariant:** The env-name list order defines precedence (alias choices before field name; first declared alias choice wins). Case normalization must be applied identically when building the lookup map and when deriving `env_name`, otherwise lookups silently miss.
**Probe:** `python3 -m pytest tests/test_settings.py -k test_merge_dict -p no:cacheprovider -q` — EXECUTED PASSING (`1 passed`); init key + env JSON merge through the same field-key path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-settings", query: "extract_field_info get_field_value env prefix alias", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the triple-based candidate ladder and the preferred-alias re-normalization (it prevents two sources writing the same field under different keys). Adapt `FieldInfo`/`AliasChoices` inspection to your metadata layer; keep the Windows downgrade only if you read the OS environ directly. Omit `env_prefix_target` unless your users need prefix-on-alias vs prefix-on-variable distinction.
