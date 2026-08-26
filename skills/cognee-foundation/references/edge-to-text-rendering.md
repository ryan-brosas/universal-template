<!-- capsule-v2 -->
# Edge-to-text rendering — stable markup the LLM and tests can parse

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How should retrieved graph edges be rendered into LLM context so node identity is unambiguous, chunks get compact titles, and the format is test-stable?

## resolve_edges_to_text
**Path/Symbol:** `cognee/modules/graph/utils/resolve_edges_to_text.py:resolve_edges_to_text` (:61-107), `_create_title_from_text` (:26-30), `_get_top_n_frequent_words` (:12-23).
**Signature:** `async resolve_edges_to_text(retrieved_edges: List[Edge]) -> str`; empty list ⇒ `""`.
**Data Shape:** Output = `Nodes:\n<per-node blocks>\n\nConnections:\n<lines>`; node block fenced with literal `__node_content_start__` / `__node_content_end__`.

### Decisive source
```python
# Bracket label is the COMPACT relationship label — never the natural-language edge_text:
edge_label = (edge.attributes.get("relationship_type")
              or edge.attributes.get("relationship_name")
              or edge.attributes.get("edge_text"))
line = f"{source_name} --[{edge_label}]--> {target_name}"
description = edge.attributes.get("edge_text")
if description and description != edge_label:
    line += f"  ({description})"          # surfaced alongside, not inside, the markup

# text-bearing nodes (chunks) get "first 7 words ... [top 3 non-stopword]":
def _create_title_from_text(text, first_n_words=7, top_n_words=3):
    return f"{' '.join(text.split()[:first_n_words])}... [{_get_top_n_frequent_words(text)}]"
```

**Flow:** dedupe nodes by id across all edges → per-node name/content resolution (text ⇒ title+full content; else name + description-fallback-name) → render node section then one connection line per edge in retrieval order.
**Invariant:** (1) The label-vs-description split is a pinned contract ("bracket label uses relationship_type not edge_text") — collapsing them regresses every consumer that parses the bracket. (2) Node identity comes from the deduped map keyed by node.id; two edges sharing an endpoint MUST render that endpoint identically. (3) Stop-word-filtered frequency titles keep chunk nodes compact without losing anchor words.
**Probe:** `cognee/tests/unit/modules/graph/test_resolve_edges_to_text.py::test_bracket_label_uses_relationship_type_not_edge_text`, `::test_edge_text_appears_as_suffix_when_different_from_label`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "resolve_edges_to_text node_content_start edge_label suffix", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fenced node blocks + compact-label-then-description line format; adapt title heuristics to your language; omit stop-word tables if you have better summarizers.
