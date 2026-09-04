<!-- capsule-v2 -->
# Plugin config + cache invalidation — how does the mypy plugin read TOML/INI config and force cache discards on plugin change?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `ext-pydantic`. **Question:** What is the config surface, and what makes mypy discard its cache when only the plugin changed?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/mypy.py:__version__ = 2` (:113), `PydanticPlugin.report_config_data` (:166-171), `PydanticPluginConfig.__init__` (:257-284).
**Signature:** `def report_config_data(self, ctx: ReportConfigContext) -> dict[str, Any]`; `PydanticPluginConfig(options: Options)` reading `[tool.pydantic-mypy]` (TOML) or `[pydantic-mypy]` (INI).
**Data Shape:** Four booleans: `init_forbid_extra`, `init_typed`, `warn_required_dynamic_aliases`, `debug_dataclass_transform`; serialized via `to_data()`.

### Decisive source
```python
# Increment version if plugin changes and mypy caches should be invalidated
__version__ = 2

def report_config_data(self, ctx: ReportConfigContext) -> dict[str, Any]:
    """Return all plugin config data. Used by mypy to determine if cache needs to be discarded."""
    return self._plugin_data

# PydanticPluginConfig: TOML first (parse_toml returns None for non-.toml files),
# else ConfigParser with getboolean fallback=False; unknown keys print a stderr warning:
unknown_keys = config.keys() - set(self.__slots__)
for key in sorted(unknown_keys):
    print(f'[pydantic-mypy]: Unrecognized option: {key} = {config[key]}', file=sys.stderr)
```

**Flow:** plugin factory `plugin(version)` ignores mypy's version string (compat is handled via `parse_mypy_version(mypy_version)` comparisons where needed) → Options.config_file parsed once per run → the dict returned by `report_config_data` is hashed into mypy's cache key, so ANY config change (or a bump of module-level `__version__`) invalidates every cached plugin result.
**Invariant:** Bumping `__version__` is the ONLY mechanism to invalidate caches after a plugin-behavior change — porters who add behavior without bumping ship stale cached signatures. Unknown user keys must warn-not-raise (forward compatibility), while wrong-typed values DO raise ValueError.
**Probe:** `grep -n '__version__ = 2' pydantic/mypy.py` (:113) + `grep -n "CONFIGFILE_KEY = 'pydantic-mypy'" pydantic/mypy.py` (:87).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic", query: "PydanticPluginConfig report_config_data cache", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the config-as-cache-key pattern and dual-format parsing; adapt option names; omit tomli fallback details for <3.11.
