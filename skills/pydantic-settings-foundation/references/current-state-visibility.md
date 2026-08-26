<!-- capsule-v2 -->
# Current-state visibility — how can one settings source react to what higher-priority sources already decided?

**Source:** pydantic-settings MIT `main@d26fc0c3944fe68cf169f86386988bb83e3df2d8`; Codebase Memory `pydantic-settings`. **Question:** How do you let a custom source (e.g. a fallback or audit source) see resolved values from earlier sources during the same resolution, without giving it write access?

## Connected graph-selected seam
**Path/Symbol:** `pydantic_settings/sources/base.py:PydanticBaseSettingsSource._set_current_state` / `current_state` / `_set_settings_sources_data` (106-212); driver `main.py:_settings_build_values` (499-535).
**Signature:** `def _set_current_state(self, state: dict[str, Any]) -> None`; `@property def current_state(self) -> dict[str, Any]`
**Data Shape:** `_current_state` holds the accumulated merge of all *previously folded* sources for this resolution; `_settings_sources_data` maps source-name → that source's raw output dict.

### Decisive source
```python
for source in sources:
    if isinstance(source, PydanticBaseSettingsSource):
        source._set_current_state(state)          # accumulated so far
        source._set_settings_sources_data(states) # name → raw output of every prior source
    ...
    source_state = source()
```
Direct test pinning behavior (`tests/test_settings.py:3450-3479`):
```python
def __call__(self) -> dict[str, Any]:
    current_state = self.current_state
    if current_state.get('one') == '1':
        return {'two': '1'}
    return {}
...
env.set('one', '1')
s = Settings()
assert s.two is True
```

**Flow:** Before each `__call__`, the kernel injects the running merged state and the per-source history into the source object. The source's `__call__` may branch on `self.current_state` (read-only in practice — mutating it corrupts the fold because the same dict object continues accumulating). Sources that are not `PydanticBaseSettingsSource` subclasses are skipped silently.
**Invariant:** Injection happens immediately before `__call__`, once per resolution pass; a source must never persist `_current_state` across resolutions (the source instance is rebuilt per `Settings()` construction). Read-don't-write: nothing in the kernel copies the state before handing it over.
**Probe:** `python3 -m pytest tests/test_settings.py -k test_settings_source_current_state -p no:cacheprovider -q` — EXECUTED PASSING (`1 passed`); pins that a later custom source sees the env-resolved value `'one' == '1'` and contributes `two`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-settings", query: "current_state set_current_state settings_sources_data", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pre-call injection pattern (two views: merged-so-far plus named history) for any pluggable resolver chain. Adapt the ownership rule to your host: pass an immutable copy if your plugins can't be trusted read-only. Omit the `DefaultSettingsSource`/`InitSettingsSource` no-op implementations of the abstract `get_field_value`.
