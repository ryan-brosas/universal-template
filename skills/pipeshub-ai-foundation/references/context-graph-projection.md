<!-- capsule-v2 -->
# Context graph projection — how do you turn a flat timeline into a "what got touched and how is it connected" graph?

**Source:** pipeshub-ai (Apache-2.0) `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** A porter reusing the timeline for post-hoc analysis must know how `TimelineEntry` rows become a typed entity graph — which events create which nodes/edges, why spawn resolution needs a pre-pass over raw order, and what the node-id/addressing scheme is.

## build_context_graph — pure timeline→ContextGraph projection
**Path/Symbol:** `context/graph_builder.py:build_context_graph` (50-116); helpers `_agent_node`/_tool_node/_file_node/_source_node_id (28-47); allowlist `_FILE_ARG_TOOLS` (21-25); data model `context/graph.py:ContextGraph/GraphNode/GraphEdge/NodeType` (17-75).
**Signature:** `build_context_graph(entries: list[TimelineEntry]) -> ContextGraph`.
**Data Shape:** Input = flat `TimelineEntry` list (any order; from `TimelineStore.get_by_trace()`/`get_by_run()`). Output = pydantic graph: `nodes: dict[str, GraphNode]` keyed by prefixed ids (`agent:<agent_id>`, `tool:<name>`, `file:<path>`, `source:<url|file|query>`), `edges: list[GraphEdge]` carrying `action` ∈ {spawned, called, blocked, touched, cited} + run_id + timestamp. Node types: AGENT/TOOL/FILE/SOURCE/ARTIFACT.

### Decisive source
```python
# graph_builder.py — the two-pass structure IS the invariant
run_to_agent: dict[str, str] = {}
for entry in entries:                       # pass 1 over RAW input order
    run_to_agent.setdefault(entry.run_id, entry.agent_id)

ordered = sorted(entries, key=lambda e: e.sequence_id)   # pass 2 in execution order
for entry in ordered:
    ...
    if entry.event_type == "agent_start" and entry.parent_run_id:
        parent_agent_id = run_to_agent.get(entry.parent_run_id)
        if parent_agent_id:                 # unknown parent ⇒ NO edge, never KeyError
            ...add_edge(GraphEdge(source_id=f"agent:{parent_agent_id}",
                                  target_id=agent_node_id, action="spawned", ...))
```

**Flow:** sort by sequence_id → every entry upserts its AGENT node → `agent_start`+parent wires `spawned` edge via the pre-pass map → `tool_call`/`tool_blocked` wire agent→tool edges (action keyed on event; blocked carries `metadata.reason`) → allowlisted file tools (`read_file`/`write_file`/`edit_file`, arg key `path`) additionally wire tool→FILE `touched` → `tool_result_sources` fans tool→SOURCE `cited` edges (one per source dict having url|file|query).
**Invariant:** `add_node` is UPSERT-with-metadata-merge (a tool called N times yields ONE node, N edges) — a porter who appends duplicate nodes or overwrites metadata breaks consumers. Spawn resolution reads RAW entries before sorting: a parent whose `agent_start` has a LATER sequence_id than its child still resolves (pinned by test). Unknown parent_run_id degrades to no-edge, not a crash. FILE nodes come ONLY from the explicit allowlist — guessing paths from arbitrary schemas would poison the graph.
**Probe:** `tests/unit/agent_loop_lib/context/test_graph_builder.py` (pins empty→empty graph; single-entry label fallback; spawned edge incl. out-of-order parent (`test_run_to_agent_lookup_is_built_before_the_ordered_pass`) and unknown-parent no-edge; blocked action + reason metadata; allowlist gating incl. non-dict args and falsy path; repeated-call node dedup; source url→file→query fallback; sequence-order edge ordering).
**Coverage caveat:** none of eval/decision consumers are unit-tested here — this test file is the direct probe for the projection only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "build_context_graph", limit: 5, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "ContextGraph add_node neighbors", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pure-function projection, the prefixed node-id scheme, the upsert-merge add_node, the run_to_agent pre-pass, and the small explicit FILE_ARG_TOOLS allowlist. Adapt the event-type vocabulary and allowlist entries to your host's tool names. Omit the ARTIFACT node type until your pipeline emits artifact events (declared but unpopulated by this builder). Direct tests confirm all invariants; index coverage `no_recorded_issue`+`metadata_match` (best-effort caveat).
