<!-- capsule-v2 -->
# Config-override no-op layer — how do I add a GUI/JSON settings layer on top of Python config WITHOUT breaking the edit-the-.py workflow?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550`; Codebase Memory `Auto_job_applier_linkedIn`. **Question:** How can a JSON file of user settings override module-level config defaults while guaranteeing the JSON can never inject new names into the config namespace and never breaks anything when absent/corrupt?

## The 55-line overlay kernel
**Path/Symbol:** `config/_overrides.py:load_user_config` (:26–36) + `apply` (:39–55); called from each `config/*.py` module at import time.
**Signature:** `load_user_config() -> dict` (never raises); `apply(module_name: str, module_globals: dict) -> None`.
**Data Shape:** `user_config.json` at project root = `{section_name: {key: value}}`; section name is derived from the module's own last dotted part (`"config.settings"` → `"settings"`).

### Decisive source
```python
def load_user_config() -> dict:
    try:
        with open(USER_CONFIG_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        return {}

def apply(module_name: str, module_globals: dict) -> None:
    section_name = module_name.split(".")[-1]
    section = load_user_config().get(section_name, {})
    if not isinstance(section, dict):
        return
    for key, value in section.items():
        if key in module_globals:
            module_globals[key] = value
```

**Flow:** every config module ends with `_overrides.apply(__name__, globals())` → missing/unreadable/non-dict JSON ⇒ `{}` ⇒ loop no-ops (classic .py-defaults behavior preserved bit-for-bit) → non-dict SECTION also no-ops → only keys ALREADY present as module globals are overwritten.
**Invariant:** the `key in module_globals` membership check IS the security boundary — user-editable JSON can never mint new config names (typo'd keys fail silent-and-harmless instead of leaking into the namespace; unknown-key rejection for the WRITE side lives in the schema-driven-config-panel capsule). Failure of the whole layer degrades to defaults, never to an exception.
**Probe:** `tests/test_config_overrides.py` — 7 tests pinning exactly this: `test_apply_overrides_only_existing_globals` (`brand_new` never introduced), `test_apply_is_noop_when_section_missing`, `test_apply_ignores_non_dict_section`, `test_apply_uses_last_dotted_part_as_section`, plus the three load_user_config missing/invalid/valid cases.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "_overrides apply load_user_config", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt verbatim for any tool that wants a settings GUI bolted onto code-first configuration — it's 55 lines with a full behavioral contract. Adapt the path derivation (`__file__`-relative root resolution). Omit nothing. Direct tests pin every guarantee.
