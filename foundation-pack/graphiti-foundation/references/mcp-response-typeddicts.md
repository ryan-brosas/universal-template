<!-- capsule-v2 -->
# Wire response TypedDicts — server boundary serialization contract

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** what wire shape must every MCP tool response satisfy so clients can parse successes and failures uniformly?

## Server response TypedDicts
**Path/Symbol:** `mcp_server/src/models/response_types.py` (:1-89): `ErrorResponse` (:8), `SuccessResponse` (:12), `NodeResult` (:16), `NodeSearchResponse` (:26), `FactSearchResponse` (:31), `EpisodeSearchResponse` (:36), `StatusResponse` (:41), `SagaSummaryResponse` (:46), `CommunityResult` (:53), `BuildCommunitiesResponse` (:60), `EdgeResult` (:67), `TripletResponse` (:79), `EpisodeEntitiesResponse` (:85).
**Signature:** all are `typing_extensions.TypedDict` (structural, zero runtime deps) — NOT pydantic models; every tool return type is a UNION `XResponse | ErrorResponse`.
**Data Shape:** success envelopes carry `message: str` + payload list; failures carry ONLY `error: str`; datetimes cross the boundary as ISO strings (`created_at: str | None`, `valid_at: str | None`, `invalid_at: str | None` on EdgeResult).

### Decisive source
```python
class ErrorResponse(TypedDict):
    error: str

class NodeResult(TypedDict):
    uuid: str
    name: str
    labels: list[str]
    created_at: str | None
    summary: str | None
    group_id: str
    attributes: dict[str, Any]     # custom typed attributes ride as free dict

class TripletResponse(TypedDict):
    message: str
    nodes: list[NodeResult]
    edges: list[EdgeResult]
```

**Flow:** core pydantic objects → per-tool `to_node_result`/`to_edge_result` converters (graphiti_mcp_server.py) → these TypedDicts → MCP JSON. The union-with-ErrorResponse pattern means callers branch on the presence of the `error` key, never on exceptions across the tool boundary.
**Invariant:** (1) failure envelope is minimal and uniform (`{'error': str}`) — adding fields to errors is a breaking change for key-checking clients; (2) temporal fields are PRE-SERIALIZED strings at this boundary — a porter returning datetime objects breaks JSON transport; (3) `attributes: dict[str, Any]` is deliberately untyped on the wire even though cores carry typed pydantic attribute models.
**Probe:** anchored at repo root. Battery: `grep -c 'class .*Response(TypedDict)' mcp_server/src/models/response_types.py` → 10; `grep -c 'class NodeResult' mcp_server/src/models/response_types.py` → 1; `grep -c 'valid_at: str | None' mcp_server/src/models/response_types.py` → 2. Direct-test coverage caveat: pure type declarations; exercised indirectly via `tests/test_core_parity.py` converters (suite env-gated here — needs `pydantic_settings`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "response_types TripletResponse FactSearchResponse to_edge_result", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-shape envelope discipline (message+payload / bare error key) and string-serialized time at any RPC/tool boundary over a pydantic core; adapt field lists to your domain objects; omit nothing — the file is fully portable as-is. Coverage caveat stated above.
