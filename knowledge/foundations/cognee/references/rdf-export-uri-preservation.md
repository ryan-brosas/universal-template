<!-- capsule-v2 -->
# RDF export — ontology_uri preservation and round-trip fidelity

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** What must the write path preserve so a memory graph can later be exported as RDF and linked to external ontologies?

## graph/rdf export + ontology_uri field
**Path/Symbol:** `cognee/modules/graph/rdf/export.py` (:1-164); preserved field `DataPoint.ontology_uri: str | None` (DataPoint.py :52-58); producer `construct_data_points_and_edges_with_ontology._add_ontology_data_points` (:202-242, sets `ontology_valid=True, ontology_uri=...`).
**Signature:** module-level export over the stored graph via rdflib.
**Data Shape:** Nodes carry `ontology_valid: bool` + stable `ontology_uri` IRI; ontology-sourced edges reuse canonical relationship names.

### Decisive source
```python
# Stable ontology IRI this node is grounded in, when it was matched to (or
# ingested from) an ontology. Preserved end-to-end so the persisted graph keeps
# the external identifier instead of collapsing it to a local label — this is
# what lets the memory graph be exported as RDF and linked out to other domains
# (open-world). None for nodes with no ontology grounding.
ontology_uri: str | None = None
```

**Flow:** ontology matching stamps `ontology_valid`/`ontology_uri` at DataPoint construction (pre-storage) → storage persists both as node properties → exporter reads them back and emits triples with the EXTERNAL IRI as identity anchor rather than minting new ones.
**Invariant:** (1) The URI must survive the full pipeline: any intermediate model that drops it breaks open-world linking permanently (the data is still there; the LINK is gone). (2) Export is read-only post-processing — nothing in cognify/search may depend on it. (3) Round-trip tests pin label↔IRI mapping.
**Probe:** `cognee/tests/unit/modules/graph/test_rdf_roundtrip.py` (whole file).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "rdf export rdflib ontology_uri roundtrip", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt end-to-end external-identifier preservation on grounded nodes; adapt serialization to your RDF dialect; omit if you never leave the property-graph world.
