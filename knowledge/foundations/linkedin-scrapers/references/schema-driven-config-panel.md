<!-- capsule-v2 -->
# Schema-driven config panel — how do I give a tool a browser/GUI settings surface WITHOUT letting the UI edit code?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550`; Codebase Memory `Auto_job_applier_linkedIn`. **Question:** How does one declarative schema render the entire control-panel UI AND power server-side validation/coercion, while the panel stays unable to touch `.py` config?

## One schema, two consumers
**Path/Symbol:** `config_schema.py:SCHEMA` (:90–267) built via `_f(...)` (:64–82); consumed by `valid_keys()` (:277–286) and `iter_fields()` (:270–274).
**Signature:** `_f(section, config_module, key, label, ftype, help, options=None, advanced=False, ai=False, models_by_provider=None) -> dict`; `valid_keys() -> {config_module: {key: field}}`.
**Data Shape:** each field dict carries `section` (UI tab), `config_module` (target config module AND the `user_config.json` section key — MUST equal the module's last dotted name), `key`, `label`, `type` ∈ {text,password,textarea,number,bool,select,list}, `help`, optional `options`/`advanced`/`ai`/`models_by_provider`. `SCHEMA = [{"section", "fields": [...]}]`.

### Decisive source
```python
def valid_keys():
    mapping = {}
    for field in iter_fields():
        mapping.setdefault(field["config_module"], {})[field["key"]] = field
    return mapping
```

**Flow:** `GET /api/schema` returns `SCHEMA` verbatim and the UI renders forms from it (`app.py:294–297`) → `POST /api/config` validates incoming `{config_module: {key: value}}` against `valid_keys()`: unknown section/key ⇒ 400 with an `unknown[]` list and NOTHING is written (`app.py:321–342`) → surviving values are coerced per declared type and merged into `user_config.json` → config modules overlay the JSON at import time (see config-override-noop-layer). The docstring states the invariant outright: "The panel NEVER edits the config/\*.py files."
**Invariant:** `config_module` is doing double duty as JSON section key and Python module name — rename either side alone and settings silently orphan. Validation is schema-driven, so adding a setting to `SCHEMA` automatically exposes it in UI + API with zero endpoint changes; conversely NO key outside the schema can ever be persisted.
**Probe:** `tests/test_app_integration.py::test_config_save_coerces_and_roundtrips` + `::test_config_save_rejects_unknown_key` (asserts 400 AND `not os.path.exists(cfg_path)` — rejection writes nothing).
**Coverage caveat:** graph resolves `config_schema._f/iter_fields/valid_keys` directly; no dedicated unit test for the schema contents themselves (they're product data pinned by the integration tests above).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "config_schema valid_keys iter_fields", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the schema-as-single-source-of-truth split (UI renders FROM the schema, API validates AGAINST the derived key map, storage is a JSON overlay — never generated code). Adapt the field-type vocabulary and the `advanced`/`ai` progressive-disclosure flags to your domain. Omit the specific field catalog (product data, ~180 entries).
