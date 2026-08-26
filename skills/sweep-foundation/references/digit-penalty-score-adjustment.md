<!-- capsule-v2 -->
# Digit-penalty score adjustment — how do you demote generated/versioned/test-numbered files without a blocklist?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** What single scoring tweak penalizes snapshot tests, build artifacts, and versioned migrations, and where must it be applied in a ranking pipeline?

## apply_adjustment_score multiplicative basename-digit decay
**Path/Symbol:** `sweepai/utils/ticket_utils.py:apply_adjustment_score` (:115–132); applied at hybrid fusion (:192–194) and rerank ingestion (:276–279).
**Signature:** `apply_adjustment_score(snippet_path: str, old_score: float) -> float`.
**Data Shape:** Input path is a snippet denotation `"<file_path>:<start>-<end>"`; only the basename (after `rsplit(":", 1)`, lowercased, last `/`-split segment) is examined.

### Decisive source
```python
file_path, *_ = snippet_path.rsplit(":", 1)
base_file_name = file_path.split("/")[-1]
if not base_file_name:
    return 0
num_numbers = sum(c.isdigit() for c in base_file_name)
snippet_score *= (1 - 1 / len(base_file_name)) ** num_numbers
```

**Flow:** every score that enters either ranking stage passes through the penalty: `(1 − 1/len)^digits` — one digit in a short name hurts proportionally more than one digit in a long name (`test_utils_3.py` decays harder than `some_long_module_v2.py`). The doc-comment enumerates the targets: numbered test files, build/snapshot outputs, versioned files, timestamp-prefixed migrations. Applied AFTER fusion weights and AGAINST raw Cohere/Voyage relevance scores, so it shapes both candidate ordering and final reranker output.
**Invariant:** It is multiplicative on an already-computed score, never additive — a zero score stays zero, and relative order among equal-digit files is preserved. The empty-basename guard returns literal `0` (not the score), killing any malformed denotation rather than trusting it.
**Probe:** No offline unit test covers this function directly (coverage caveat; `tests/search/` harnesses need live keys). Deterministic probe at pin: `grep -cn 'apply_adjustment_score' sweepai/utils/ticket_utils.py` → 3 (definition + two call sites).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "apply adjustment score penalty digits file name", limit: 5 });
// executed at pin: apply_adjustment_score ticket_utils.py 115-132, single definition,
// consumed inside multi_get_top_k_snippets and get_pointwise_reranked_snippet_scores
```

## Verdict
Adopt the basename-digit multiplicative decay applied at BOTH pre-rerank fusion and post-rerank ingestion — porting it into only one stage leaves versioned files resurfacing after reranking. Adapt the exponent shape to your filename conventions. Omit the `rsplit(":", 1)` if your snippets carry whole-file paths instead of line-range denotations.
