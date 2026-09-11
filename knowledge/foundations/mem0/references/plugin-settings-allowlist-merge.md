<!-- capsule-v2 -->
# Settings allowlist merge — how do you accept user config without inheriting junk keys?

**Source:** mem0 Apache-2.0 `main@7e096155`; Codebase Memory `mem0`. **Question:** what is the minimal safe loader for a user-editable JSON settings file?

## Connected graph-selected seam
**Path/Symbol:** `integrations/mem0-plugin/scripts/load_settings.py`: DEFAULTS (:13-21), `load_settings` (:24-34), `create_default_settings` (:37-45), `unknown_keys` (:48-59). Tests `tests/test_load_settings.py` (8 passed offline).
**Signature:** `load_settings() -> dict`; `unknown_keys() -> list[str]`; `create_default_settings() -> bool`.
**Data Shape:** DEFAULTS schema {auto_save, auto_search, search_limit:10, retention_session_days:90, confidence_threshold:0.3, global_search:false, debug:false}.

### Decisive source
```python
settings = dict(DEFAULTS)
if SETTINGS_PATH.exists():
    try:
        with open(SETTINGS_PATH) as f:
            user = json.load(f)
    except (json.JSONDecodeError, OSError):
        return settings                      # malformed → pure defaults
    if isinstance(user, dict):
        settings.update({k: v for k, v in user.items() if k in DEFAULTS})   # allowlist
...
return sorted(k for k in user if k not in DEFAULTS)   # unknown_keys(): keys NO code reads
```

**Flow:** defaults copy → parse user file → non-dict or unreadable ⇒ defaults → merge ONLY known keys → CLI `init` creates once (`Created` printed exactly once across runs) and warns about ignored keys.
**Invariant:** unknown keys NEVER enter effective config but ARE reported back to the user (typo surfacing); creation never overwrites an existing file; every failure mode returns usable defaults.
**Probe:** `cd $REFERENCE_ROOT/mem0 && .venv/bin/python -m pytest integrations/mem0-plugin/tests/test_load_settings.py -q` (executed this pass: 8 passed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "mem0", qualified_name: "mem0.integrations.mem0-plugin.scripts.load_settings.load_settings" });
```

## Verdict
Adopt allowlist-merge + unknown-key reporting + create-once defaults for any user-editable config; adapt the DEFAULTS roster and file location; omit the mem0 key meanings.
