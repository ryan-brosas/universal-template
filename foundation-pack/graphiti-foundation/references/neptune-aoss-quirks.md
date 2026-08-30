<!-- capsule-v2 -->
# Neptune/AOSS quirks ledger — which three latent traps live in the Neptune path and what does a porter verify instead of copying?

**Source:** Graphiti Apache-2.0 `main@401c59a` (`neptune_driver.py`, `nodes.py`, `node_db_queries.py`); Codebase Memory `graphiti`. **Question:** Before adopting the Neptune integration, which known-buggy or fragile behaviors must be checked/reproduced rather than trusted?

## Known-trap inventory with decisive lines
**Path/Symbol:** `run_aoss_query`/`save_to_aoss` module-global mutation (`neptune_driver.py:342–364`); entity_edges delimiter bug (`nodes.py:699` + `EPISODIC_NODE_RETURN_NEPTUNE`); un-awaited coroutine ladder (`neptune_driver.py:313–318`).
**Signature:** `save_to_aoss(self, name: str, data: list[dict]) -> int`; `delete_all_indexes_impl` declared `async`.
**Data Shape:** `aoss_indices[...]` templates are dicts mutated per call; `EPISODIC_NODE_RETURN_NEPTUNE` projects `entity_edges` as a comma-joined string.

### Decisive source
```python
def run_aoss_query(self, name: str, query_text: str, limit: int = 10) -> dict[str, Any]:
    for index in aoss_indices:
        if name.lower() == index['index_name']:
            index['query']['query']['multi_match']['query'] = query_text   # MUTATES MODULE STATE
            query = {'size': limit, 'query': index['query']}
            resp = self.aoss_client.search(body=query['query'], index=index['index_name'])
            return resp
    return {}
```
and the coroutine trap:
```python
def delete_all_indexes(self) -> Coroutine[Any, Any, Any]:
    return self.delete_all_indexes_impl()

async def delete_all_indexes_impl(self) -> Coroutine[Any, Any, Any]:
    # No matter what happens above, always return True
    return self.delete_aoss_indices()          # BUG: missing await — returns coroutine object
```

**Flow:** TRAP 1 — query/save templates are shared module globals: `run_aoss_query` writes the caller's query text INTO the template before searching. Two interleaved searches (async tasks sharing one driver) can race the template mutation; single-loop usage masks it. TRAP 2 — Neptune stores multi-value `entity_edges` as comma-joined strings and `get_episodic_node_from_record` splits on `,` (:699 area), while edge FACTS can themselves contain commas → field-splitting corruption; the existing `neptune-encoding-traps.md` documents the name_embedding half of this encoding family, this row completes the entity_edges side. TRAP 3 — `delete_all_indexes_impl` returns `self.delete_aoss_indices()` without awaiting, so the "always" cleanup silently becomes a no-op coroutine unless a caller awaits the returned value twice-nested.
**Invariant:** none of these are guarded upstream — they are LATENT. The capsule's invariant is procedural: anyone porting this driver audits all three sites and fixes them in the port (deep-copy the template per call; pick a lossless delimiter/encoding; await-or-drop the ladder).
**Probe:** coverage caveat — no direct test exercises any of the three sites (Neptune e2e disabled in `tests/helpers_test.py:60`). Deterministic probes: grep the port for `index['query']['query']...= query_text` (must be absent), for `return self.delete_aoss_indices()` inside an async fn (must be awaited).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "aoss_indices run_aoss_query delete_all_indexes", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the audit checklist, not the code: deep-copy per-request query state, lossless-list encoding, explicit awaits. Adapt the delimiter choice to your graph's escaping rules. Omit the "No matter what happens above, always return True" comment as documentation — the code does not do what the comment claims; comments lose to source.
