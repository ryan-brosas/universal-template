<!-- capsule-v2 -->
# YAML settings source — env-var expansion inside config files with source-priority ladder

**Source:** graphiti MIT `main@401c59a`; Codebase Memory `graphiti`. **Question:** how do you let one YAML file hold secrets/flags via `${VAR}` / `${VAR:-default}` references while keeping CLI > env > file > defaults precedence in pydantic-settings?

## Connected graph-selected seam
**Path/Symbol:** `mcp_server/src/config/schema.py`: `YamlSettingsSource` (:16), `_expand_env_vars` (:23), `GraphitiConfig.settings_customise_sources` (:293), `apply_cli_overrides` (:308); `graphiti_mcp_server.py`: `initialize_server` (:1098) sets `os.environ['CONFIG_PATH']` (:1178) before constructing the settings object.
**Signature:** `YamlSettingsSource(settings_cls, config_path: Path | None = None)` subclassing `PydanticBaseSettingsSource`; `__call__() -> dict[str, Any]`; `settings_customise_sources(...) -> tuple[PydanticBaseSettingsSource, ...]`.
**Data Shape:** YAML values may embed `${VAR}` or `${VAR:default}`; a value that is ENTIRELY one expression is type-coerced (true/1/yes/on → True, false/0/no/off → False, empty → None for optional fields), while partial substitutions stay strings; recursion covers dicts and lists.

### Decisive source
```python
full_match = re.fullmatch(pattern, value)
if full_match:
    result = replacer(full_match)
    if isinstance(result, str):
        if lower_result in ('true', '1', 'yes', 'on'):  return True
        elif lower_result in ('false', '0', 'no', 'off'): return False
        elif lower_result == '': return None   # env unset → optional field default
    return result
else:
    return re.sub(pattern, replacer, value)    # keep partial substitution a string
...
# Priority: CLI args (init) > env vars > yaml > dotenv
return (init_settings, env_settings, yaml_settings, dotenv_settings)
```

**Flow:** process start → `--config` arg written into `CONFIG_PATH` env → settings instantiation pulls the custom source tuple (YAML slotted between env and dotenv) → YAML loaded with `yaml.safe_load`, recursively env-expanded, returned as a plain dict that pydantic validates against nested models (`env_nested_delimiter='__'` gives flat env vars like `LLM__PROVIDER` precedence over it).
**Invariant:** the full-match/partial-match split is the porting trap — coercing a partially-substituted string to bool would corrupt composite values; and the source ORDER tuple is the entire precedence contract (file-based sources must never precede env). Missing YAML file returns `{}` so defaults flow through untouched.
**Probe:** `mcp_server/tests/test_configuration.py::test_config_loading` (YAML load + `LLM__PROVIDER`/`LLM__MODEL` env override wins).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "graphiti", query: "YamlSettingsSource settings_customise_sources apply_cli_overrides", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the custom-settings-source pattern whenever config files must reference environment secrets without a templating step. Adapt the coercion tables and delimiter to your framework. Omit the legacy `apply_cli_overrides` hasattr-ladder if your CLI parser feeds init kwargs directly.
