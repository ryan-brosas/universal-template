<!-- capsule-v2 -->
# Impact summary — how do you answer "what breaks if I change X?" in one query?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What does build_impact_summary compute and how does hop_to_risk map distance to severity?

## Inbound BFS + depth→risk mapping
**Path/Symbol:** tests/test_store_search.c:851 (`store_hop_to_risk`), 863 (`store_build_impact_summary`); engine near cbm_store_bfs.
**Signature:** impact summary built from inbound traversal of a node + per-hop classification.
**Data Shape:** Summary: direct dependents, transitive counts per hop level, risk class derived from hop depth (closer ⇒ higher risk). Risk mapping is a pure function so callers can re-derive it.

### Decisive source
```c
TEST(store_hop_to_risk) { ... }
TEST(store_build_impact_summary) { ... }
```

**Flow:** resolve target → inbound BFS (CALLS/USAGE) recording first-reach depth → bucket nodes by depth → apply hop→risk mapping → emit summary. detect_changes composes this with hunk-scoped seeds for diff-driven answers.
**Invariant:** First-reach depth only — a node reached at hop 1 and hop 3 counts ONCE at the closer hop; risk classes are ordinal labels, never numeric scores presented as precision.
**Probe:** the two named tests plus hunk-seed composition in tests/test_mcp.c:7431.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "impact", limit: 5 });
```

## Verdict
Adopt BFS-bucketed impact with explicit risk vocabularies; adapt thresholds; keep the pure risk function separate for testability.
