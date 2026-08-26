<!-- capsule-v2 -->
# Entity node extraction & resolution — dedup and attribution

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** how do entities enter the graph and survive deduplication?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/utils/maintenance/node_operations.py` (1,032 lines): `extract_nodes` (:70-141); `graphiti_core/nodes.py` (1,122 lines): `Node` (:93), `EpisodeType` (:54).
**Signature:** `extract_nodes(episode, ...)` — accepts one episode or MANY; a list concatenates contents for ONE LLM extraction call while the FIRST episode supplies metadata.
**Data Shape:** extraction prompt chosen by episode source type (message/json/text) with a silent fallback to text (`# Fallback to text extraction` :271) so new `EpisodeType` members never break ingestion; nodes dedup by `__hash__`/`__eq__`.

### Decisive source
```ts
# extract_nodes: one batched call, attribution built in
# a list gets its contents concatenated for ONE LLM extraction call
# while the FIRST episode supplies metadata
# prompt chosen by episode source type — message/json/text — with a silent
# fallback to text (# Fallback to text extraction :271)
```

**Flow:** `extract_nodes` batches episodes into one LLM extraction call (first episode supplies metadata), chooses the prompt by source type (with a text fallback), then resolves/dedups nodes by hash/eq. `Node.validate_labels` guards label shape.
**Invariant:** a list of episodes is extracted in one batched call; new episode types never break ingestion (silent text fallback); nodes dedup by hash/eq.
**Probe:** `tests/` node tests (batched extraction; source-type prompt selection; fallback; dedup).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "extract_nodes episode batch LLM prompt fallback dedup nodes", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the batched node extraction (one LLM call, first-episode metadata, source-type prompt + text fallback) and dedup; adapt the prompt templates and node schema to host.
