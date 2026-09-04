<!-- capsule-v2 -->
# Ontology canonicalization — collapse LLM nodes onto the ontology BEFORE graph construction

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** Where in the ingestion flow must ontology matching happen so matched entities merge into one node instead of spawning duplicates?

## canonicalize_extracted_graphs → construct → enrich
**Path/Symbol:** `cognee/modules/ontology/construct_data_points_and_edges_with_ontology.py:construct_data_points_and_edges_with_ontology` (:318-338), `_canonicalize_extracted_graph` (:98-153), `add_ontology_data_points_and_edges` (:276-315).
**Signature:** `(data_chunks, extracted_graphs, resolver) -> (dict[str,DataPoint], dict[EdgeIdentity,Edge])`.
**Data Shape:** `OntologyMatch{node_category: "classes"|"individuals", canonical_name, canonical_uri, ontology_nodes, ontology_edges, first_source_chunk}`; lookup keyed `(category, generate_node_name(extracted_name))`.

### Decisive source
```python
# canonicalize IN PLACE before ordinary construction:
node.name = entity_match.canonical_name
canonical_entity_id = Entity.id_for(entity_match.canonical_name)
surviving = surviving_node_id_by_entity_id.get(canonical_entity_id)
if surviving is None:
    surviving_node_id_by_entity_id[canonical_entity_id] = node.id   # first survives
else:
    surviving_node_id_by_collapsed_node_id[node.id] = surviving
# then re-point every edge endpoint through the survivor map:
edge.source_node_id = collapsed.get(edge.source_node_id, edge.source_node_id)
```

**Flow:** match each distinct (category, normalized name) once via `resolver.get_subgraph` (fuzzy strategy: exact hit first, else `difflib.get_close_matches(cutoff=0.8)`) → rewrite node names/types to canonical → collapse same-canonical nodes and re-point edges → run the ORDINARY `construct_data_points_and_edges` on canonicalized graphs (so all dedup machinery is reused) → add ontology subgraph nodes/edges (`ontology_valid=True`, `ontology_uri` preserved for RDF export), one subgraph per unique root key.
**Invariant:** (1) Canonicalization must precede construction — after construction the entities are already distinct DataPoints and merging means a delete+rewrite. (2) Node types are ALSO canonicalized through the classes category so EntityType nodes merge. (3) Resolver config precedence: explicit `config["ontology_config"]["ontology_resolver"]` wins, else env triple (path + resolver + strategy ALL required); default install ships NO resolver ⇒ pure path.
**Probe:** `cognee/tests/unit/modules/ontology/test_ontology_adapter.py::test_find_closest_match_no_match`; wiring pinned by cognify route tests (`get_configured_ontology_resolver` call at cognify.py :257).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "canonicalize_extracted_graphs ontology match collapse surviving", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pre-construction canonicalization with survivor edge re-pointing; adapt match strategy (cognee's only shipped one is fuzzy-difflib); omit RDFLib specifics if your ontology store differs.
