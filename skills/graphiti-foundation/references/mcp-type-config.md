<!-- capsule-v2 -->
# MCP type-config bridge — env-configured types into core's typed extraction args

**Source:** graphiti MIT `main@401c59a`; Codebase Memory `graphiti`. **Question:** how do you accept entity/edge types as plain config (name + description) and turn them into the `dict[str, type[BaseModel]]` / `edge_type_map` shapes core expects, without losing LLM-visible semantics?

## Connected graph-selected seam
**Path/Symbol:** `mcp_server/src/utils/type_config.py`: `parse_reference_time` (:29), `coerce_group_ids` (:52), `_doc_only_model` (:67), `build_entity_types` (:79), `build_edge_types` (:101), `build_edge_type_map` (:121), `build_fact_search_filters` (:163).
**Signature:** `build_entity_types(configs: list[EntityTypeConfig] | None) -> dict[str, type[BaseModel]] | None`; `_doc_only_model(name: str, description: str) -> type[BaseModel]` = `create_model(name)` with `model.__doc__ = description`; `coerce_group_ids(group_ids: str | list[str] | None) -> list[str] | None`.
**Data Shape:** config entries are `{name, description}` pairs; output maps type name → Pydantic model (registered rich model preferred, doc-only fallback otherwise); `edge_type_map` becomes `{(source, target): [edge_type_names]}` with `'Entity'` as endpoint wildcard; date filters become `SearchFilters` with `list[list[DateFilter]]` (outer OR, inner AND).

### Decisive source
```python
def _doc_only_model(name, description):
    model = create_model(name)
    model.__doc__ = description      # graphiti-core surfaces the DOCSTRING to the extraction LLM
    return model

def coerce_group_ids(group_ids):
    if isinstance(group_ids, str):
        return [group_ids] if group_ids else None   # '' → None → default group,
    return group_ids                                # NOT group '' (matters for clear_graph)
```

**Flow:** YAML/env config lists `{name, description}` per type → for each name, look up a hand-registered rich model in `models/entity_types.py` `ENTITY_TYPES` / `models/edge_types.py` `EDGE_TYPES` → miss falls back to a fieldless `create_model` whose docstring carries the description into prompts → `add_episode` receives real Pydantic models; search tools get `parse_reference_time`-normalized UTC datetimes and OR/AND nested date filters.
**Invariant:** three porting traps pinned here: (1) the doc-only fallback must set `__doc__`, because that string is what the extraction LLM actually sees — dropping it silently degrades typing; (2) blank-string group_ids must normalize to `None` (config default), never to `['']`, or destructive ops like clear_graph target group `''`; (3) builders return `None` (not `{}`) when unconfigured so core keeps its DEFAULT extraction behavior — an empty dict would suppress it.
**Probe:** `mcp_server/tests/test_core_parity.py::TestBuildEntityTypes::test_unknown_name_falls_back_to_doc_only_model`, `TestCoerceGroupIds::test_blank_string_is_treated_as_omitted`, `TestBuildFactSearchFilters::test_valid_at_range_is_and_group`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "graphiti", query: "build_entity_types build_edge_type_map coerce_group_ids parse_reference_time", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the registry-preferred/doc-fallback pattern for exposing typed schemas through config, and the strict normalization rules (`''→None`, None-not-empty-dict). Adapt the registered-model names to your domain. Omit nothing structural; this file is deliberately I/O-free so it unit-tests without a live DB.
