<!-- capsule-v2 -->
# project-config-toml-roundtrip — How does per-project config survive edits without destroying formatting or comments?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** Why tomlkit, what does filter_none do, and what is the write-back merge rule?

## Config roundtrip seam
**Path/Symbol:** `gpt_engineer/core/project_config.py:Config.to_toml` (:122-151), `filter_none` (:59-69), `read_config` (:154-158); filename constant `gpt-engineer.toml` (:11).
**Signature:** `Config.from_toml(path) -> Config`; `Config.to_toml(config_file, save=True) -> str`.
**Data Shape:** Sections [run] build/test/lint/format, [paths] base/src, [gptengineer-app] project_id/openapi[]; dataclasses mirror sections exactly.

### Decisive source
```python
config = read_config(config_file)           # tomlkit PRESERVES comments/ordering
default_config = Config().to_dict()
for k, v in self.to_dict().items():
    # only write values that are already explicitly set, or that differ from defaults
    if k in config or v != default_config[k]:
        if isinstance(v, dict):
            config[k] = {k2: v2 for k2, v2 in v.items()
                         if (k2 in config[k] or default_config.get(k) is None or v2 != default_config[k].get(k2))}
        else:
            config[k] = v
toml_str = tomlkit.dumps(config)
```
```python
def filter_none(d):  # drops None values and BECAME-empty dicts, recursively
    return {k: v for k, v in ((k, filter_none(v) if isinstance(v, dict) else v)
                              for k, v in d.items() if v is not None)
            if not (isinstance(v, dict) and not v)}
```

**Flow:** load existing doc (comments intact) → overlay only explicitly-set-or-non-default values → dump string (optionally write) → to_dict renames python field gptengineer_app ⇄ toml key gptengineer-app and filter_nones empties.
**Invariant:** (1) tomlkit (NOT stdlib tomli/toml for WRITES — stdlib `toml` pkg used in file_selector for READS) chosen specifically because dumps preserves user comments/layout across programmatic edits; mixing writers corrupts that guarantee. (2) Write-back merge: existing keys always kept; new keys written only when differing from defaults — prevents config-file bloat with boilerplate. (3) gptengineer-app section REQUIRES project_id (asserted in from_dict) — app integration config fails loud at parse. (4) filter_none must run BEFORE dumps because tomlkit.dumps raises on None values.
**Probe:** `grep -n 'import tomlkit' gpt_engineer/core/project_config.py` → :9.
**Probe:** `grep -n 'only write values' gpt_engineer/core/project_config.py` → :131 comment pinning merge intent.
**Probe:** `tests/test_project_config.py` exercises roundtrips.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "project_config Config to_toml filter_none tomlkit", limit: 10 });
```

## Verdict
Adopt comment-preserving roundtrip + non-default-only write-back for user-facing config files; adapt schema; keep the two-library split (read-anywhere vs write-preserving) explicit if you consolidate — losing comments is the regression to guard.
