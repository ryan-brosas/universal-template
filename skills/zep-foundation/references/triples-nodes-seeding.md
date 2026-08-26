<!-- capsule-v2 -->
# Fact triples & node seeding — how do you assert known facts and canonical entities deterministically?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** When LLM extraction is the wrong tool, what contracts govern direct fact/node writes and their returned identities?

## FactTriple / NodeItem / ingest_nodes
**Path/Symbol:** `ingestion/src/zep_ingest/triples.py:31` (`MAX_FACT_CHARS=250`), `:36` (`_FACT_NAME`), `:40` (`FactTriple`), `:118` (`to_api_kwargs`), `:162` (`ingest_fact_triples`); `nodes.py:32` (`NodeItem`), `:58` (`to_add_node_item`), `:92` (`_assigned_node_uuids`), `:113` (`ingest_nodes`, MAX_NODES_PER_REQUEST=100).
**Signature:** fact_name MUST match `^[A-Z][A-Z0-9_]*$` (SCREAMING_SNAKE_CASE); node/endpoint names ≤50 chars, facts ≤250, summaries ≤500; labels ≤1 entity-type ("extraction assigns one best-match type per node").
**Data Shape:** `source_node_uuid`/`target_node_uuid` pin endpoints by identity instead of name resolution; Zep assigns node/fact UUIDs server-side (supplying them is a retired-field error naming the replacement).

### Decisive source
```python
# _assigned_node_uuids — always ``expected`` long, aligned with the request
# batch: a missing entry is None so callers can zip against the submitted
# nodes without shifting later identities forward over a gap.
# nodes.py ingest_nodes:
result._node_uuids_from_submit = True
if error is not None:
    result.node_uuids.extend([None] * len(batch))   # keep slots aligned
    continue
result.node_uuids.extend(_assigned_node_uuids(response, expected=len(batch)))
```

**Flow:** triples: validate all BEFORE first call → sequential graph.add_fact_triple (the Batch API does not accept triples) → task_id collected or untracked_items++ . nodes: batch ≤100 via graph.add_nodes → response UUIDs extracted positionally with None gaps → task_id tracked. Both return IngestResult whose wait() recovers edge_uuids from completed task params in task_ids order.
**Invariant:** Use cases are explicit: "product catalogs, org charts, seeding canonical entities before a corpus ingest — where LLM extraction is the wrong tool". Identity pinning via UUIDs exists "so a re-run cannot resolve a slightly different name to a new node". Parallel-lists-with-None-gaps beats any clever compaction because downstream zip() must not shift.
**Probe:** `grep -c 'def test' ingestion/tests/test_triples.py ingestion/tests/test_nodes.py | awk -F: '{s+=$2} END{print s}'` → 51.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "FactTriple add_fact_triple add_nodes assigned uuids", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt eager SCREAMING_SNAKE validation + UUID endpoint pinning + gap-slotted returned identities; adapt limits/naming grammar to your ontology; omit Zep task-param recovery if your API is synchronous.
