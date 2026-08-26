<!-- capsule-v2 -->
# Input validation gates — group_id/label regex guards + protected attribute names

**Source:** graphiti MIT `main@401c59a`; Codebase Memory `graphiti`. **Question:** which strings must be validated before they reach Cypher/labels, where do the guards fire, and what can a custom entity type NOT name its fields?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/helpers.py`: `validate_group_id` (:136), `validate_group_ids` (:162), `validate_node_labels` (:174); `graphiti_core/errors.py`: `GroupIdValidationError` (:78), `NodeLabelValidationError` (:86, note: subclasses GraphitiError AND ValueError), `EntityTypeValidationError` (:70); `graphiti_core/utils/ontology_utils/entity_types_utils.py`: `validate_entity_types` (:23).
**Signature:** `validate_group_id(group_id: str | None) -> bool` — empty string allowed (default case), else `^[a-zA-Z0-9_-]+$` or raise; `validate_entity_types(entity_types: dict[str, type[BaseModel]] | None) -> bool`.
**Data Shape:** node labels must start with letter/underscore and contain only alphanumerics/underscores (label-injection guard); entity-type field names are checked against `EntityNode.model_fields.keys()`.

### Decisive source
```python
# helpers.py:136 — empty string is VALID (means "use default"), anything not
# matching the allowlist raises:
if not re.match(r'^[a-zA-Z0-9_-]+$', group_id):
    raise GroupIdValidationError(group_id)
...
# entity_types_utils.py:23 — a custom type may not shadow core node fields:
entity_node_field_names = EntityNode.model_fields.keys()
for entity_type_field_name in entity_type_model.model_fields.keys():
    if entity_type_field_name in entity_node_field_names:
        raise EntityTypeValidationError(entity_type_name, entity_type_field_name)
```

**Flow:** every search entry point (`search/search.py:110`, `search_utils.py:86`, FalkorDB fulltext builder :64) calls `validate_group_ids` before query construction; label lists are validated inside `SearchFilters` validators (`search_filters.py:71`, also re-checked in filter-combining paths :95/:138); `Graphiti.add_episode` (:1070-1071) validates entity types AND excluded-entity-types before any extraction work.
**Invariant:** validation happens at the BOUNDARY (before string interpolation into queries/labels), not at persistence — a porter who moves these checks after query building inherits an injection surface; empty-string group_id must remain legal because it encodes "fall back to provider default"; `NodeLabelValidationError` deliberately multiply-inherits ValueError so it satisfies both except styles.
**Probe:** `tests/test_node_label_security.py::test_node_label_validation` (labels starting with non-letter rejected), `tests/utils/search/test_search_security.py:59` (`GroupIdValidationError` on bad chars), `mcp_server/tests/test_core_parity.py::TestEntityTypeRegistration::test_configured_entity_types_avoid_reserved_field_names`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "graphiti", query: "validate_group_id validate_node_labels validate_entity_types GroupIdValidationError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt boundary-time allowlist validation for any string that becomes a query fragment or label, and the reserved-field-name check for user-supplied schemas. Adapt the regex to your store's identifier grammar. Omit nothing — these ~100 lines are the cheapest security win in the repo.
