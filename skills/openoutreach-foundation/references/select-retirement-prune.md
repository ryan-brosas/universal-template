<!-- capsule-v2 -->
# Node retirement & anti-monotone prune — what does an exhausted query mean for its subtree?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** When a conjunctive query comes back empty, which related queries does that verdict convict — and how do you enforce it when the node lattice is a DAG, not a tree?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/pipeline/select.py:retire` (:437-465), `_prune_descendants` (:468-488), `_dead_sets` (:326-341), `expand` (:382-416), `_upsert` (:358-379), `token_key` (:81-89).
**Signature:** `retire(node, *, at_offset: int) -> "dead"|"drained"|"capped"`; `expand(node, store, candidates) -> int`; `token_key(keywords) -> sha256 hex`.
**Data Shape:** REACH_CAP = 10_000 (Elasticsearch `index.max_result_window`, measured); states DEAD/DRAINED/FRONTIER/FIRED.

### Decisive source
```python
if at_offset == 0:
    node.state = QueryNode.State.DEAD          # index matches NOBODY
    _prune_descendants(node); return "dead"
node.state = QueryNode.State.DRAINED           # every match is already a Lead here
if at_offset < REACH_CAP:
    _prune_descendants(node); return "drained"
return "capped"                                # hit the 10k window — subtree STAYS

# at creation time (covers DAG supersets parent-links can't reach):
child_set = frozenset(child_pairs)
if any(empty <= child_set for empty in dead):  # superset of an empty conjunction is empty
    pruned += 1; continue
```

**Flow:** empty page → retire() by offset → dead/drained prune the whole subtree breadth-first via parent links; capped retires the node only because adding a token opens a fresh 10k window over the unreachable part. Expansion re-checks dead sets so supersets reached through a *different* parent are still pruned.
**Invariant:** Retirement is a corpus fact, never a model fact — nothing is retired for scoring badly. The three zero-cases are not interchangeable: capped ≠ drained (a capped node's children open fresh windows; a drained node's children are already in the DB). Dedup on canonicalized `token_key` (`json.dumps(sorted(pairs))`) makes most nodes reachable several ways, which is exactly why creation-time subset checks are load-bearing rather than a dedup nicety. Multi-path nodes keep the parent with the **highest** estimate (optimism; the parent is a claim about a region and the best-supported claim wins).
**Probe:** `tests/test_select.py::TestRetirement` (:330-377), `TestExpansion::test_children_are_the_node_plus_one_co_occurring_token` (:278-287), `TestTokenKey` (:43-54).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "retire node", limit: 5 });
```

## Verdict
Adopt the offset-keyed retirement semantics and the anti-monotone dead-set check at creation; adopt canonical-set hashing as node identity. Adapt the reach cap to your provider's real paging window; omit Django bulk-update mechanics.
