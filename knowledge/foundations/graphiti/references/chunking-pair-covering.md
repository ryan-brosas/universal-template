<!-- capsule-v2 -->
# Pair-covering chunk design — greedy set-cover over item pairs with sampling fallback

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** how do you partition N items into chunks of ≤K so that EVERY PAIR of items co-occurs in at least one chunk — with bounded work and a guaranteed-completion fallback?

## Pair-covering chunk design (covering design)
**Path/Symbol:** `graphiti_core/utils/content_chunking.py`: `generate_covering_chunks` (:719-826), `_random_combination` (:714-716), `MAX_COMBINATIONS_TO_EVALUATE = 1000` (:711); direct suite `tests/utils/test_content_chunking.py::TestGenerateCoveringChunks` (:465-780).
**Signature:** `generate_covering_chunks(items: list[T], k: int) -> list[tuple[list[T], list[int]]]` — each element is `(chunk_items, global_indices)` preserving provenance into the original list.
**Data Shape:** uncovered state is a `set[frozenset[int]]` of index pairs; `n <= k` short-circuits to one chunk `(items, range(n))`; Schönheim lower bound documented: `F >= ceil(N/K * ceil((N-1)/(K-1)))`.

### Decisive source
```python
# Greedy round: pick the candidate chunk covering the most still-uncovered pairs.
# Exhaustive enumeration ONLY when C(n,k) is small; otherwise sample:
total_combinations = comb(n, k)
use_sampling = total_combinations > MAX_COMBINATIONS_TO_EVALUATE
...
max_total_attempts = MAX_COMBINATIONS_TO_EVALUATE * 3   # duplicate-sample guard
while samples_evaluated < MAX_COMBINATIONS_TO_EVALUATE:
    total_attempts += 1
    if total_attempts > max_total_attempts: break        # anti-infinite-loop
    chunk_indices = _random_combination(n, k)            # sorted tuple
    if chunk_indices in seen_combinations: continue
...
if best_chunk_indices is None or best_covered_count == 0:
    break   # sampling found nothing covering -> exit to fallback

# GUARANTEE: any pairs the greedy missed are covered by minimal size-2 chunks:
for pair in uncovered_pairs:
    pair_indices = sorted(pair)
    chunks.append(([items[idx] for idx in pair_indices], pair_indices))
```

**Flow:** trivial case → enumerate all C(n,k) combinations (or sample ≤1000 distinct, ≤3000 attempts) scoring each by newly-covered pair count → commit the best chunk, discard its pairs from the uncovered set → repeat until uncovered is empty OR no candidate covers anything → flush remaining pairs as explicit two-item chunks → return chunks with global index maps.
**Invariant:** (1) full pair coverage is UNCONDITIONAL — the size-2 fallback exists precisely because random sampling can stall; a port that drops the fallback can silently lose coverage; (2) `_random_combination` returns a SORTED tuple so identical sets compare equal in `seen_combinations` (duplicate-sampling safety); (3) coverage bookkeeping uses `frozenset([i,j])` — order-free pairs — while OUTPUT indices stay sorted tuples; (4) work is bounded on BOTH paths (exhaustive only under `comb(n,k) <= 1000`).
**Probe:** `.venv/bin/python -m pytest tests/utils/test_content_chunking.py::TestGenerateCoveringChunks -q` (k=2/k=3/large-N all-pairs coverage, index-mapping correctness, greedy minimality vs Schönheim, determinism, custom generic types, k15/n30 sampling, fallback pair-chunks, duplicate-sampling safety, multi-seed stress). Anchored at repo root. Battery: `grep -c 'MAX_COMBINATIONS_TO_EVALUATE = 1000' graphiti_core/utils/content_chunking.py` → 1; `grep -c 'max_total_attempts = MAX_COMBINATIONS_TO_EVALUATE \* 3' graphiti_core/utils/content_chunking.py` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "generate_covering_chunks uncovered_pairs combinations sampling", limit: 5, fields: ["signature", "name", "file"] });
// rank-1 line-exact :719-826 + TestGenerateCoveringChunks :465-780
```

## Verdict
Adopt the greedy-with-fallback set-cover skeleton and the index-map return shape whenever an LLM budget forces pairwise-relation mining into batches; adapt K and the sampling cap to your token budget; omit exhaustive mode if inputs always exceed the threshold. Direct tests run in default CI.
