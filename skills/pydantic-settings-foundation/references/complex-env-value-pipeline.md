<!-- capsule-v2 -->
# Complex-value pipeline — JSON decode, delimiter explosion, and deep merge for nested fields

**Source:** pydantic-settings MIT `main@d26fc0c3944fe68cf169f86386988bb83e3df2d8`; Codebase Memory `pydantic-settings`. **Question:** When a field is a model/dict, when is its env value JSON-parsed versus built by splitting `FIELD__SUB__KEY` variables — and what happens when both exist?

## Connected graph-selected seam
**Path/Symbol:** `pydantic_settings/sources/providers/env.py:EnvSettingsSource.prepare_field_value` (119-163), `explode_env_vars` (269-340); shared decode gate `sources/base.py:PydanticBaseSettingsSource.decode_complex_value`.
**Signature:** `def prepare_field_value(self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool) -> Any`
**Data Shape:** input single env string or `None`; `explode_env_vars` returns a nested dict keyed by delimiter-split segments (`env_nested_max_split` bounds the split count via `str.split(sep, maxsplit)`).

### Decisive source
```python
else:
    # field is complex and there's a value, decode that as JSON, then add explode_env_vars
    try:
        value = self.decode_complex_value(field_name, field, value)
    except ValueError:
        if not allow_parse_failure:
            raise

    if isinstance(value, dict):
        return deep_update(value, self.explode_env_vars(field_name, field, self.env_vars))
```

**Flow:** For a complex field: no value → try `explode_env_vars` alone; scalar/JSON value → attempt `json.loads` (skipped when the field opts out with `NoDecode`, or globally with `enable_decoding=False` unless `ForceDecode` is present) then deep-merge the decoded dict with exploded vars; simple fields skip all of this and go through `_coerce_env_val_strict`. During explosion, each intermediate segment navigates via `next_field` to find the sub-`FieldInfo`; leaf complexity decides per-leaf JSON decoding with an `allow_json_failure` ladder, and an AliasPath-head match forces complex decoding so pydantic can index into containers (#670).
**Invariant:** Exploded vars must be filtered by exact `field_env_name + delimiter` prefix (prefix computed from `_extract_field_info`, stripped before splitting so prefix characters overlapping the delimiter are safe). A non-dict JSON result (e.g. a list) is returned as-is, never merged. Missing required complex fields raise standard validation errors downstream.
**Probe:** `python3 -m pytest tests/test_settings.py -k test_env_nested_dict_value -p no:cacheprovider -q` — EXECUTED PASSING (`1 passed`); pins `nested__foo__a__b=bar` → `{'nested': {'foo': {'a': {'b': 'bar'}}}}`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-settings", query: "explode env vars nested delimiter next_field", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-way branch (no-value → explode only; value → decode + deep-merge explode; simple → coerce) and per-leaf complexity checks. Adapt `next_field`'s model introspection to your schema objects; keep `maxsplit` bounded if your keys may contain the delimiter in leaf values. Omit enum-name→value rewriting (`env_parse_enums`) unless you accept Literal[Enum] fields.
