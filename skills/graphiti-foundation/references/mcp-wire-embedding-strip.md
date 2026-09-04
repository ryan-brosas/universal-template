<!-- capsule-v2 -->
# MCP wire serialization — double embedding strip, ISO-or-None datetimes

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** how does the MCP server keep multi-kilobyte embeddings and non-JSON datetime objects out of tool responses — and why does stripping happen twice?

## Connected graph-selected seam
**Path/Symbol:** `mcp_server/src/utils/formatting.py` (82L): `to_node_result` (:11), `to_edge_result` (:26), `format_node_result` (:41), `format_fact_result` (:64); consumers `graphiti_mcp.py` tool handlers; envelope types `models/response_types.py:NodeResult/EdgeResult` (owned by `mcp-response-typeddicts.md`).
**Signature:** `to_node_result(node: EntityNode) -> NodeResult` / `format_node_result(node: EntityNode) -> dict[str, Any]` — TypedDict builders for typed envelopes vs model_dump for passthrough dicts.
**Data Shape:** both families emit datetimes as `x.isoformat() if x else None`; attributes dict is passed through EXCEPT anything whose key lowercased contains 'embedding'.

### Decisive source
```python
# formatting.py :41-60 — strip at BOTH layers
def format_node_result(node: EntityNode) -> dict[str, Any]:
    result = node.model_dump(
        mode='json',
        exclude={'name_embedding'},          # layer 1: known model field
    )
    # Remove any embedding that might be in attributes
    result.get('attributes', {}).pop('name_embedding', None)  # layer 2:
    return result                            # customer-supplied attributes
                                             # can smuggle the SAME key

# :14 — attribute-side catch-all
attrs = {k: v for k, v in attrs.items() if 'embedding' not in k.lower()}
# to_edge_result :26-39 — every datetime is isoformat()-or-None, three fields
```

**Flow:** tool handler receives EntityNode/EntityEdge from a search → either builds a typed NodeResult/EdgeResult (explicit field list; embeddings never named) or calls format_* (`model_dump(mode='json', exclude={...})`) → second pop guards the free-form `attributes` map where user-defined entity types may carry their own `name_embedding`/`fact_embedding` keys → response envelope serializes clean.
**Invariant:** (1) embeddings are stripped TWICE because pydantic `exclude=` only covers declared fields — custom entity-type schemas put undeclared keys into `attributes`, so a single-layer strip leaks 1024-float vectors into every node payload; (2) the attribute filter matches SUBSTRING case-insensitively ('embedding' in k.lower()) so `<entity>_embedding` variants die too; (3) missing datetimes serialize as None, present ones as ISO strings — never epoch floats, never raw datetime objects (MCP JSON layer would raise); (4) `.pop(key, None)` non-destructive default keeps the formatter total on absent keys.
**Probe:** `cd /mnt/hdd/utopia/inspo/memory/graphiti && grep -c "'name_embedding'" mcp_server/src/utils/formatting.py` → `2`; `grep -o "embedding" mcp_server/src/utils/formatting.py | wc -l` → `10` (includes fact_embedding twin + docstrings); `grep -c "if 'embedding' not in k.lower()" mcp_server/src/utils/formatting.py` → `1`. Coverage caveat: NO direct unit test file exists for this module under `mcp_server/tests/` (factories/config/transports suites don't import it) — pinned by source read only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "format_node_result to_node_result exclude name_embedding", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt two-layer exclusion (declared-field exclude + free-form-dict substring sweep) for any payload sanitizer sitting between rich domain models and a JSON wire; adapt field names to your schema. A porter copying only the model_dump line ships vector payloads as soon as users define custom entity types.
