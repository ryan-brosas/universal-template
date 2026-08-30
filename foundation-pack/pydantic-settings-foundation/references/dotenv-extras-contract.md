<!-- capsule-v2 -->
# Dotenv extras contract — what happens to .env variables that match no declared field?

**Source:** pydantic-settings MIT `main@d26fc0c3944fe68cf169f86386988bb83e3df2d8`; Codebase Memory `pydantic-settings`. **Question:** A .env file usually carries app vars the settings model never declares — how does the dotenv source pass them through (or not) without breaking `extra='forbid'` models, and how do multiple files order?

## Connected graph-selected seam
**Path/Symbol:** `pydantic_settings/sources/providers/dotenv.py:DotEnvSettingsSource` (27-186; extras loop in `__call__`), `_read_env_files`, `_static_read_env_file`.
**Signature:** `def __call__(self) -> dict[str, Any]` (extends `EnvSettingsSource.__call__` output).
**Data Shape:** `_load_env_vars` returns one flat map: per-file `dotenv_values(...)` dicts updated in file-list order (later file wins); values already passed through `parse_env_vars`.

### Decisive source
```python
if is_extra_allowed and env_name.startswith(self.env_prefix):
    # env_prefix should be respected and removed from the env_name
    normalized_env_name = env_name[len(self.env_prefix):]
    data[normalized_env_name] = env_value
else:
    data[env_name] = env_value
```
with the claim guard just above it:
```python
and self.env_nested_delimiter
and env_name.startswith(f'{field_env_name}{self.env_nested_delimiter}')
```

**Flow:** After the inherited per-field loop, every remaining non-empty dotenv var is tested: skip if already claimed by a field or if a declared field's name collides under prefixing; mark "used" only when it sits at a nested-delimiter boundary of a complex field (`db__x` claims for field `db`; a bare `dbx_token` must NOT be claimed and survives as an extra). Extras are emitted with the prefix stripped when `extra != 'forbid'` and a prefix is set, else verbatim. Two filtering modes short-circuit this: `dotenv_filtering='only_existing'` returns exactly the inherited field-matched data; `'match_prefix'` adds all prefixed vars (stripping the prefix) that aren't already present or inside an already-populated nested group.
**Invariant:** Multi-file precedence is last-file-wins (shallow `dict.update` per file). The delimiter-boundary guard is load-bearing: removing it silently swallows near-colliding extras. Missing files are skipped without error (`_resolve_config_file` returning `None`).
**Probe:** `python3 -m pytest tests/test_settings.py -k test_dotenv_extra_allow_complex_field_nested_delimiter_boundary -p no:cacheprovider -q` — EXECUTED PASSING (`1 passed`); `tests/test_settings.py:3556-3572`: `db__host` is consumed into field `db`, while `db_host` and `dbx_token` survive as extras.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-settings", query: "dotenv extra env_prefix filtering only_existing match_prefix", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the extras-claim algorithm including the boundary guard and the `extra != 'forbid'` gate. Adapt the file-order policy if you need first-wins instead of last-wins. Omit `dotenv_filtering` modes unless porting the 2025-era config surface they were added for.
