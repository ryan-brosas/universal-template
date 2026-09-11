<!-- capsule-v2 -->
# Config validation ladder — how do I fail fast and loudly on a misconfigured automation config before the bot touches the network?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550f8aa80027621cfc17a30fceba05705f84` (`modules/validator.py` 221L). Codebase Memory `Auto_job_applier_linkedIn`. **Question:** what typed-checker ladder and per-file validation functions catch bad config values with actionable error messages before any scraping starts?

## Typed checker ladder + per-file validators
**Path/Symbol:** `modules/validator.py:check_int` (:24–27), `check_boolean` (:29–31), `check_string` (:33–37), `check_list` (:39–46), `validate_personals` (:51–75), `validate_questions` (:79–103), `validate_search` (:107–148), `validate_secrets` (:154–168), `validate_settings` (:172–202), `validate_config` (:207–220). **Signature:** `check_int(var, var_name, min_value=0) -> bool | TypeError | ValueError`; `validate_config() -> bool` runs all five validators.
**Data Shape:** each checker raises `TypeError` for wrong type and `ValueError` for out-of-range/not-in-options; error messages embed the source config file path and the exact fix ("open config/personals.py and update first_name to be an Integer"). `check_list` validates element types and membership too.

### Decisive source
```python
def check_int(var, var_name, min_value=0):
    if not isinstance(var, int):
        raise TypeError(f'The variable "{var_name}" in "{__validation_file_path}" must be an Integer! ...')
    if var < min_value:
        raise ValueError(f'The variable "{var_name}" in "{__validation_file_path}" expects an Integer >= {min_value}! ...')
    return True

def check_string(var, var_name, options=[], min_length=0):
    if not isinstance(var, str): raise TypeError(...)
    if min_length > 0 and len(var) < min_length: raise ValueError(...)
    if len(options) > 0 and var not in options: raise ValueError(f'Expecting a value from {options}, not {var}!')
    return True

def validate_config():
    validate_personals(); validate_questions(); validate_search()
    validate_secrets(); validate_settings()
    return True
```

**Flow:** each `validate_<file>()` sets the module-global `__validation_file_path` to its config file, then calls the typed checkers against every imported variable (e.g. `check_string(first_name, "first_name", min_length=1)`, `check_boolean(pause_before_submit, ...)`, `check_list(experience_level, "experience_level", [...options])`); `validate_config()` runs all five in dependency order so a bad personal detail fails before a bad search filter.
**Invariant:** the error message is self-diagnosing — it names the config file, the variable, the received value/type, and the exact edit to make (including the "don't quote integers" note). This turns a silent misconfiguration (which would otherwise surface as a confusing runtime failure mid-scrape) into a loud, actionable startup error. Options lists are the source of truth for enum-like config (ethnicity, gender, us_citizenship, sort_by, experience_level, etc.).
**Probe:** no upstream tests — coverage caveat recorded. Graph anchors resolve: `check_int`, `check_string`, `check_list`, `validate_config`, `validate_search`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "check_int", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "validate_config", limit: 5 });
```

## Verdict
Adopt the typed-checker ladder with self-diagnosing error messages and the per-file validator split; adapt the option lists and variable names to host config; omit the config files themselves (personals.py/secrets.py are gitignored personal data). Caveat: source-grounded only, no test coverage.
