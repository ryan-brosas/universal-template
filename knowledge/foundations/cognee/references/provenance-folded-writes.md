<!-- capsule-v2 -->
# Provenance-folded writes — atomic source-ref stamping and the ledger-before-write rule

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How does a write path guarantee every stored artifact carries its (dataset, data, run) ownership so rollback can find it — without a window where an artifact exists unattributed?

## add_data_points provenance paths
**Path/Symbol:** `cognee/tasks/storage/add_data_points.py:add_data_points` (:39-260), ref-key format `cognee/infrastructure/databases/provenance/source_refs.py:make_source_ref_key` (:6-8), `EdgeIdentity` (`delete_data.py:6-12`).
**Signature:** `async add_data_points(data_points, custom_edges=None, embed_triplets=False, ctx=None, graph_only=False)`; `make_source_ref_key(dataset_id, data_id) -> f"{SOURCE_REF_PREFIX}:{dataset_id}:{data_id}"` (split(":") parsers validate prefix+version).
**Data Shape:** Three write modes: hybrid (`add_nodes_with_vectors`), graph_only (no vector engine), split (graph + vector gathered). `data_item_id(data_item)` resolves `.id` (relational Data) or `.data_id` (ingestion DataItem); None ⇒ attribution impossible ⇒ both ledger and fold paths skipped.

### Decisive source
```python
stores_provenance = await mark_graph_provenance_if_empty(graph_engine)
if not stores_provenance:
    # Ledger written BEFORE the graph/vector writes so a failed write
    # can always be swept by the rollback handler:
    async with get_async_session() as session:
        await upsert_nodes(nodes, ..., pipeline_run_id=pipeline_run_id, session=session)
        await upsert_edges(edges, ..., session=session)
        await session.commit()

# Graph provenance is folded INTO the graph write (atomic — no write-then-attach
# window, no concurrent lost update — COG-5522 #4/#8):
fold_source_ref_key = make_source_ref_key(dataset.id, data_id)
await graph_engine.add_nodes(nodes, source_ref_key=fold_source_ref_key,
                             pipeline_run_id=fold_run_arg)
```

**Flow:** resolve engines/capability → provenance gate → (ledger path) one transaction for all upserts → write nodes+edges (+vector indexing gathered concurrently; `model_copy(deep=True)` before handing to indexer) → hybrid backends attach refs in a SECOND pass (`attach_node_source_refs`/`attach_edge_source_refs`) accepting the documented write-then-attach window; attach failure marks the run failed.
**Invariant:** (1) Non-hybrid graphs MUST fold the source ref into the add call itself — atomic stamping is what eliminates the lost-update window. (2) The relational ledger precedes artifact writes: reversed order makes failed writes unsweepable. (3) `embed_triplets` builds `Triplet` datapoints with text `"{src} -› {rel}-›{tgt}"` and id `generate_node_id(src+rel+tgt)` — deterministic dedup. (4) `graph_only=True` forbids `embed_triplets` (raises).
**Probe:** `cognee/tests/unit/tasks/chunks/test_create_chunk_associations_provenance.py`; storage tests `cognee/tests/unit/modules/storage/`; contract tests `cognee/tests/unit/infrastructure/databases/provenance/test_provenance_contract.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "add_data_points fold_source_ref_key attach_node_source_refs upsert_nodes", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt atomic in-write provenance folding where your store supports it, else ledger-before-write ordering; adapt ref-key encoding (colon-versioned string) to your ids; omit S3 push and triplet embedding if unused.
