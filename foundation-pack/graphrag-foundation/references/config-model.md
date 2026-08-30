<!-- capsule-v2 -->
# Config model — per-feature pydantic configs + Defaults classes + strategy resolution

**Source:** graphrag MIT `<branch>@<commit>`; Codebase Memory `graphrag`. **Question:** how does a big pipeline keep one YAML config comprehensible — per-feature sections, central defaults, and named model references instead of inline credentials?

## Connected graph-selected seam
**Path/Symbol:** `graphrag/config/models/graph_rag_config.py`: `GraphRagConfig` (:40) — `completion_models: dict[str, ModelConfig]` (:51), `embedding_models: dict[str, ModelConfig]` (:56), `concurrent_requests` (:61), plus one field per feature (`extract_graph`, `cluster_graph`, `community_reports`, `local_search`, ...); per-feature models in `config/models/*_config.py` (e.g. `ExtractGraphConfig` :22 with `completion_model_id` :25 referencing the dict above); defaults centralized in `config/defaults.py` (`ExtractGraphDefaults` :143, `BasicSearchDefaults` :57, ...) consumed via `graphrag_config_defaults`; loading in `config/load_config.py:14`.
**Signature:** every feature config is a small BaseModel whose model-valued fields reference entries in `GraphRagConfig.completion_models` BY NAME (`model_instance_name`) — never inline provider config.
**Data Shape:** nested pydantic dump = the YAML; `Field(description=...)` doubles as generated docs; strategies use `DefaultForStrategies`-style dicts so per-workflow overrides live beside global ones.

### Decisive source
```ts
class GraphRagConfig(BaseModel):
    completion_models: dict[str, ModelConfig] = Field(default=defaults.completion_models)
    embedding_models:  dict[str, ModelConfig] = Field(default=defaults.embedding_models)
    extract_graph: ExtractGraphConfig = ...   # each feature gets its own section
# ExtractGraphConfig:
    completion_model_id: str   # -> key into GraphRagConfig.completion_models
    entity_types: list[str] = Field(default=..., description=...)
    max_gleanings: int = Field(...)
```

**Flow:** YAML → `load_config` merges file/env/cli layers into `GraphRagConfig` (pydantic fills any absent field from `graphrag_config_defaults.*`) → workflows read only their own feature section and resolve `completion_model_id` against the shared model registry → one model definition can serve many features.
**Invariant:** models are declared once and referenced by id (no duplicated credentials per feature); every setting has a code-owned default (YAML only overrides); adding a feature = adding one config class + one Defaults entry.
**Probe:** `tests/` config tests (missing sections fall back to defaults; model-id references resolve; env/cli override precedence).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "GraphRagConfig ModelConfig completion_models load_config defaults", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the named-model-registry + per-feature-section + centralized-Defaults config pattern; adapt the layering (file/env/cli) to host conventions.
