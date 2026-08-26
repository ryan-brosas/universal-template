<!-- capsule-v2 -->
# Shared config loader ladder — how do I load settings.yaml/yml/json with env overlay, overrides, and cwd semantics without re-deriving the failure ladder?

**Source:** graphrag (MIT) `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory project `graphrag`. **Question:** What is the exact resolution → dotenv → env-substitution → parse → merge → chdir order graphrag-common imposes on every settings file?

## load_config — one generic loader behind every package config
**Path/Symbol:** `packages/graphrag-common/graphrag_common/config/load_config.py`: `load_config` (:106-205), `_default_config_files` (:18), `_get_config_file_path` (:29-45), `_load_dotenv` (:48-55), `_parse_env_variables` (:85-91), `_get_parser_for_file` (:68-82), `_recursive_merge_dicts` (:94-103), `ConfigParsingError(ValueError)` (:21-26). Re-exported by `packages/graphrag/graphrag/config/load_config.py`.
**Signature:** `load_config(config_initializer: Callable[..., T], config_path=None, overrides=None, set_cwd=True, parse_env_vars=True, load_dot_env_file=True, dot_env_path=None, config_parser=None, file_encoding="utf-8") -> T`.
**Data Shape:** raw file TEXT flows through env substitution BEFORE parsing (so `${VAR}` works inside comments-free scalar positions only); parsed dict merges `overrides` IN PLACE; final `config_initializer(**config_data)` builds the typed model.

### Decisive source
```python
_default_config_files = ["settings.yaml", "settings.yml", "settings.json"]   # priority order

def _parse_env_variables(text: str) -> str:
    try:
        return Template(text).substitute(os.environ)      # ${VAR} syntax, os.environ mapping
    except KeyError as error:                             # missing var → typed failure
            raise ConfigParsingError(f"Environment variable not found: {error}") from error
        # NOTE: invalid $-syntax raises RAW ValueError that ESCAPES this funnel (probed)

def _recursive_merge_dicts(dest, src):                    # IN PLACE; lists REPLACE, never element-merge
    for key, value in src.items():
        if isinstance(value, dict):
            if isinstance(dest.get(key), dict): _recursive_merge_dicts(dest[key], value)
            else: dest[key] = value
        else: dest[key] = value

# tail of load_config — process-global side effect, then typed construction
if set_cwd:
    os.chdir(config_path.parent)
return config_initializer(**config_data)                  # pydantic ValidationError passes through RAW
```

**Flow:** resolve path (file wins; dir scans yaml→yml→json; none ⇒ FileNotFoundError) → optional `.env`: REQUIRED only when caller passed explicit `dot_env_path`, implicit sibling `.env` is best-effort (:48-55) → env substitution → parser dispatch on `suffix.lower()` (`.json`|`.yaml`|`.yml` ONLY — the unsupported-extension message falsely advertises `.toml`) → parse errors wrapped `ConfigParsingError` → recursive override merge → default `os.chdir(config_dir)` → typed initializer.
**Invariant:** env substitution happens on TEXT before parsing (one pass, fail-closed on missing vars); overrides deep-merge dicts but REPLACE scalars AND lists wholesale; `set_cwd=True` mutates PROCESS cwd so relative paths inside configs resolve against the config location.
**Probe:** `tests/unit/load_config/test_load_config.py` — both failure ladders, happy paths, list-replacement (`len(nested_list)==1` after 1-item override :124), cwd change assertion (:111-118), env substitution via fixtures (`config_with_env.yaml`+`test.env`). EXECUTED pre-write: suite **passed** within the 13-test run; plus live semantic probes: `_recursive_merge_dicts({'a':{'x':1,'y':2}}, {'a':{'y':9,'z':3}})` → `{'a':{'x':1,'y':9,'z':3}}`; missing var → `ConfigParsingError`; `$ 100 dollars` → raw ValueError escaped.

## Get live surrounding code
**Retrieve:** (executed live; rank-line-exact)
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "load_config ConfigParsingError dotenv environment variable parse", limit: 10 });
// rank#1 _load_dotenv :48-55; #2 _parse_json :58-60; #3 _parse_yaml :63-65;
// #4 _parse_env_variables :85-91; #5 ConfigParsingError.__init__ :24-26
```

## Verdict
Adopt text-level `${VAR}` substitution before parsing, required-vs-best-effort dotenv duality, wholesale list replacement in overrides, and the explicit chdir contract (or make it opt-in like the test does with `set_cwd=False`). Adapt the filename priority list and parser set. Omit nothing silently: fix the `.toml` message lie and catch Template's ValueError in a port. Extends the one-line loading pointer in the config-model capsule with the actual mechanism.