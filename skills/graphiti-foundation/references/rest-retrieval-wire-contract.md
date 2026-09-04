<!-- capsule-v2 -->
# REST retrieval wire contract — INVERTED chat templates, UTC-forced facts, required-Optional trap

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `graphiti`. **Question:** what exactly crosses the HTTP boundary on retrieval, and where do the formatting and typing traps live?

## Connected graph-selected seam
**Path/Symbol:** `server/graph_service/routers/retrieve.py` — `/search`, `/entity-edge/{uuid}`, `/episodes/{group_id}`, `/get-memory` (:17-56), `compose_query_from_messages` (:59-63); `server/graph_service/dto/retrieve.py` — `FactResult` (:16-29 with UTC json_encoders), `GetMemoryRequest` (:36-44).
**Signature:** all fact endpoints funnel through `get_fact_result_from_edge(edge)` (trace_path: callers = search, get_entity_edge, get_memory) → `FactResult{uuid,name,fact,valid_at,invalid_at,created_at,expired_at,source_node_uuid,target_node_uuid,episodes}`.
**Data Shape:** every datetime is serialized by `json_encoders = {datetime: lambda v: v.astimezone(timezone.utc).isoformat()}`; episodes defaults via `Field(default_factory=list)` after `edge.episodes or []` coalescing.

### Decisive source
```python
# retrieve.py :62 — READ side puts role_type outside, role inside:
combined_query += f'{message.role_type or ""}({message.role or ""}): {message.content}\n'
# ingest.py :61 — WRITE side puts role outside, role_type inside:
episode_body=f'{m.role or ""}({m.role_type}): {m.content}',
# PROBE P2' at this pin: write 'alice(user): hello world' vs read
# 'user(alice): hello world\n' -> NOT equal. The parallel-looking
# templates are INVERTED.
#
# dto/retrieve.py :39-41 — LATENT TRAP: '...' default makes this REQUIRED
# despite Optional typing; no handler ever reads it:
center_node_uuid: str | None = Field(
    ..., description='The uuid of the node to center the retrieval on'
)
```

**Flow:** /get-memory concatenates the caller's chat transcript into one plain-text query → `graphiti.search(group_ids=[group_id], query=combined_query, num_results=max_facts)` → edges projected field-by-field into FactResults → pydantic serializes datetimes with the UTC-forcing encoder. The two f-strings were clearly MEANT to mirror each other (same punctuation shape), so queries would resemble ingested episode text — but the fields are swapped, so when both role and role_type are set, query text never matches stored episode bodies.
**Invariant:** (1) write/read format symmetry is a retrieval-quality mechanism that must be EXACT — graphiti shows how easy it is to ship a near-miss (probe-verified inversion at this pin); port with ONE shared template constant, not two hand-rolled f-strings; (2) time strings are forced to UTC ISO AT THE BOUNDARY (same contract as MCP TypedDicts; see `mcp-response-typeddicts`) — and because `astimezone` runs on every value, NAIVE datetimes are silently reinterpreted through the server's system timezone before conversion (probe P4: naive 12:00 became 04:00+00:00 on a UTC+8 box); require tz-aware inputs upstream; (3) pydantic-v2 `Field(...)` overrides Optional typing: omitting `center_node_uuid` from /get-memory is a 422 despite the nullable type (probe P3: ValidationError:missing) and handlers never read it — dead weight gating every request; (4) `/search` takes plural `group_ids` while `/get-memory` takes singular `group_id` — two partition conventions exposed simultaneously.
**Probe:** probes P1–P4 executed this pass against real sources under the repo root venv (fastapi/pydantic_settings module-import shims disclosed; tested logic uses neither): P1 worker exec-then-drain `(True, 1, True)`; P2' template inversion printed above; P3 `ValidationError:missing`; P4 `2026-01-01T04:00:00+00:00`. Direct tests: none unit-level (live int test only needs FalkorDB+OpenAI key) — coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "graphiti", name_pattern: "^(FactResult|GetMemoryRequest|SearchQuery|compose_query_from_messages)$", fields: ["signature"] });
```

## Verdict
Adopt write/read format symmetry ONLY as a single shared constant — this repo proves the drift risk is real even three meters apart. Force UTC serialization once in the DTO layer but demand tz-aware datetimes upstream. Audit every `Optional + Field(...)` inbound combo: pydantic makes it required, and dead required fields are API-breaking accidents waiting to ship.
