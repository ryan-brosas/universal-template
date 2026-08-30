<!-- capsule-v2 -->
# Frontier Beta smoothing + Thompson draw — how do you rank candidate queries from sparse per-node feedback?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** How do you score thousands of rarely-fired query nodes against each other when almost every node has zero or a handful of labelled outcomes?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/pipeline/select.py:_beta_params` (:232-244), `estimate` (:247-261), `next_node` (:283-321), `LabelStore.base_rate` (:174-190), `frontier` (:266-280).
**Signature:** `estimate(node, store, cache=None) -> float`; `_beta_params(node, store, cache) -> tuple[float, float]`; `next_node(campaign, store, rng=None) -> QueryNode | None`.
**Data Shape:** node = set of `(field, token)` keywords with `parent_id`, `state ∈ {FRONTIER, FIRED, DEAD, DRAINED}`, `next_offset`.

### Decisive source
```python
def _beta_params(node, store, cache):
    a, b = store.counts(node.pairs)                       # qualified / rejected containing ALL tokens
    level = estimate(node.parent, store, cache) if node.parent_id else store.base_rate
    return a + 2 * level, b + 2 * (1 - level)             # P̂(node) = (a + 2·P̂parent)/(a+b+2)

# sampling is Thompson over the same two numbers — the Beta params ARE the smoothed estimate:
score = rng.beta(alpha, beta) if THOMPSON else alpha / (alpha + beta)
```

**Flow:** frontier() loads ONE global pool (unfired children ∪ fired veins with pages left; no remove move) → score every node → Thompson draw sorts → fire best. A vein that stops paying accumulates `b` and sinks on its own; deepening and opening are the same arithmetic.
**Invariant:** The Laplace budget of 2 is pointed at the **parent's rate**, not 0.5 — parent supplies the level, child's own counts move it off, so thin evidence stays near its parent instead of swinging to 0/1. `base_rate` is itself smoothed ((sum+1)/(n+2)) and that is load-bearing: a campaign whose every verdict is a rejection reads raw 0, which makes α=0 for every unlabelled node — not a distribution; smoothing fixes it for the whole walk by induction. Counts beat embeddings here: measured head-to-head on 4,100 edges, smoothed counts pearson 0.661 vs GP-on-keywords 0.450, and counts+0.15·GP-delta 0.660 ≈ counts alone — **the GP is gone from choosing queries but still produces the labels counted**. No root: the empty query is never fired (its one 10k window is the provider's famous-company head); base_rate stands in for it.
**Probe:** `tests/test_select.py::TestEstimate` (:172-214), `TestFrontier::test_next_node_is_none_when_nothing_is_fireable` (:228-231).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "next_node", limit: 5 });
```

## Verdict
Adopt parent-pointed Laplace smoothing as the recursion rule, Thompson draws over the same Beta (one line, nothing to tune, width tracks evidence), and the single global frontier pool without a remove move. Adapt what a "label" means to your domain; omit the roadmap-card measurement history and the debug frontier dump unless porting the walk verbatim.
