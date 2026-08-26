<!-- capsule-v2 -->
# Dataset file round-trip — how do YAML/JSON files preserve a typed eval dataset (and its editor schema pointer) without losing custom types?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How does pydantic_evals represent a dataset on disk vs at runtime, and how does the `$schema` sidecar survive both directions?

## Runtime/wire split + `$schema` two-channel round-trip
**Path/Symbol:** `pydantic_evals/pydantic_evals/dataset.py:_CaseModel/_DatasetModel` (:89-107), `from_file/from_text/from_dict` (:557-666), `to_file` (:747-794), `_save_schema` (:846-864), `_add_json_schema` (:902-913), `_infer_fmt` (:877-900), `_params` (:535-554).
**Signature:** `Dataset.from_file(path, fmt=None, custom_evaluator_types=(), custom_report_evaluator_types=()) -> Self`; `_add_json_schema(self, nxt, info) -> dict` (`@model_serializer(mode='wrap')`).
**Data Shape:** Runtime `Case` is a plain dataclass held inside a pydantic `Dataset[InputsT, OutputT, MetadataT]`; wire layer is `_DatasetModel` with `$schema` aliased onto `json_schema_path`, `extra='forbid'`.

### Decisive source
```python
# wire model accepts the schema key it later emits
class _DatasetModel(BaseModel, Generic[...], extra='forbid'):
    json_schema_path: str | None = Field(default=None, alias='$schema')

# save: YAML gets a comment line; JSON gets the key injected first-in-order
if fmt == 'yaml':
    dumped_data = self.model_dump(mode='json', by_alias=True, context={'use_short_form': True})
    content = yaml.dump(dumped_data, sort_keys=False, allow_unicode=True)
    if schema_ref:
        content = f'{_YAML_SCHEMA_LINE_PREFIX}{schema_ref}\n{content}'   # '# yaml-language-server: $schema='
else:
    context['$schema'] = schema_ref
    json_data = self.model_dump_json(indent=2, by_alias=True, context=context)

# wrap serializer: only injects when the caller passed it via serialization context
if isinstance(context, dict) and (schema := context.get('$schema')):
    return {'$schema': schema} | nxt(self)
return nxt(self)
```

**Flow:** load = suffix dispatch (`_infer_fmt`: .yaml/.yml/.json else ValueError prescribing `fmt`) → text → YAML forks to `yaml.safe_load`+`from_dict`, JSON validates straight into the cached generic `_serialization_type()` → `_from_dataset_model` resolves evaluator specs against a per-call registry → runtime graph. Save = infer fmt → resolve schema ref (relative template verbatim; absolute-under-parent relativized by recursive `_get_relative_path_reference`) → write sidecar ONLY if content differs (`_save_schema` compares before writing) → dump with context. Name falls back to `path.stem` when absent.
**Invariant:** The `$schema` value travels through DIFFERENT channels per format (YAML comment line vs JSON dict key) but both must be re-absorbable: the alias accepts the JSON key back, and the YAML comment is ignored by safe_load. A porter who emits `$schema` unconditionally breaks plain dumps; who forgets the alias gets `extra='forbid'` validation failures on their own files.
**Probe:** `tests/evals/test_dataset.py::test_serialization_to_json` (:1023-1039) asserts `raw['$schema']` is a str pointing at an EXISTING sidecar; `test_deserializing_without_name` (:1005-1020) pins stem fallback; `test_serialization_errors` (:1087-1093) pins the exact inference error.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "Dataset _add_json_schema serialization", limit: 8 });
```
Live check this pass: search_graph rank set resolved `_CaseModel`/`_DatasetModel` (:89-107) and `_add_json_schema` (:902-913); check_index_coverage `no_recorded_issue` for dataset.py.

## Verdict
Adopt the two-layer split (runtime object graph + narrow wire model), format fork, and dual-channel `$schema` contract. Adapt path templates and the yaml-language-server prefix to your host's conventions. Omit logfire-span plumbing. Coverage caveat: none — file fully indexed and read whole.
