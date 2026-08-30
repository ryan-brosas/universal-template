<!-- capsule-v2 -->
# File-config providers — how do JSON/TOML/YAML sources get alias-aware key handling for free?

**Source:** pydantic-settings MIT `main@d26fc0c3944fe68cf169f86386988bb83e3df2d8`; Codebase Memory `pydantic-settings`. **Question:** Why do file-based config sources respect `validation_alias` and case-insensitive keys, and how should multiple files be merged?

## Connected graph-selected seam
**Path/Symbol:** `pydantic_settings/sources/base.py:ConfigFileSourceMixin` (215-239); `sources/providers/json.py:JsonConfigSettingsSource` (23-50) as the canonical subclass; multi-file parent search `sources/utils.py:_resolve_config_file` (80-96).
**Signature:** `class JsonConfigSettingsSource(InitSettingsSource, ConfigFileSourceMixin)`; `def _read_files(self, files: ConfigFileSourceType | None, deep_merge: bool = False) -> dict[str, Any]`
**Data Shape:** `_read_files` folds per-file dicts into one map (shallow `update`, or recursive merge when `deep_merge=True`) which is then handed to `InitSettingsSource.__init__` *as if it were init kwargs*.

### Decisive source
```python
self.json_data = self._read_files(self.json_file_path, deep_merge=deep_merge)
super().__init__(settings_cls, self.json_data, _init_state=_init_state)   # InitSettingsSource
```
and the fold inside the mixin:
```python
updating_vars = self._read_file(file_path)
if deep_merge:
    vars = deep_update(vars, updating_vars)
else:
    vars.update(updating_vars)
```

**Flow:** Constructor resolves the file path from kwarg or `model_config['json_file']` → reads/merges files → delegates to `InitSettingsSource`, whose alias-normalization loop maps raw file keys to preferred validation aliases, honors `populate_by_name`, drops duplicates case-insensitively, and passes unknown keys through as extras. `__call__` then just returns those normalized kwargs. Missing files are skipped silently (`if not file_path.is_file(): continue`); `_resolve_config_file(file, depth)` additionally searches `Path.cwd().parents[:depth]` for relative names (absolute paths never searched; dotenv passes `allow_fifo=True`).
**Invariant:** A file source is an InitSettingsSource wearing a reader — that inheritance is the entire reason file keys behave like constructor kwargs. Multi-file order is first-listed-first-read with later files overriding (shallow) unless `deep_merge` is set; nested structures are NOT merged by default.
**Probe:** `python3 -m pytest tests/test_source_json.py -p no:cacheprovider -q` — EXECUTED PASSING (`9 passed`); repository-owned provider suite exercising `_read_files` ordering, deep merge, and alias handling.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-settings", query: "config file mixin read files json toml yaml deep merge", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mixin+init-inheritance shape — it deletes an entire class of alias-handling bugs when adding a new file format. Adapt the parser (`_read_file` is the only abstract member; implement it with your TOML/YAML/JSON library). Omit `deep_merge` only if single-file configs are guaranteed.
