<!-- capsule-v2 -->
# Trajectory scoring modes — how do you score an agent's tool sequence from exact-match down to order-blind F1?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** What are the exact semantics of the three trajectory-comparison modes, including their empty-input edge cases and reproducible-reason format?

## exact / in_order (LCS-F1) / any_order (multiset-F1)
**Path/Symbol:** `pydantic_evals/pydantic_evals/evaluators/agentic.py:TrajectoryMatch.evaluate` (:324-366); `_longest_common_subsequence_length` (:263-277); `_f1` (:280-283); mode type `TrajectoryOrder` (:251-260).
**Signature:** `evaluate(ctx) -> EvaluationReason` with float value in [0,1]; `_longest_common_subsequence_length(a: list[str], b: list[str]) -> int` (rolling 1-D DP).
**Data Shape:** expected = user list; actual = span-derived name list (start-time ordered); reason strings embed `LCS=`, `overlap=`/precision/recall/F1 to three decimals plus both lists so a score can be recomputed from the text.

### Decisive source
```python
if not actual and not expected:
    return EvaluationReason(value=1.0, reason='both actual and expected trajectories are empty')
if self.order == 'any_order':
    overlap = sum((Counter(expected) & Counter(actual)).values())
    precision = overlap / len(actual) if actual else 0.0
    recall = overlap / len(expected) if expected else 0.0
    ...
# order == 'in_order'
lcs = _longest_common_subsequence_length(actual, expected)
```

**Flow:** `'exact'` → list equality gives 1.0/0.0 (checked BEFORE the empty-pair branch, with its own explicit reason) → `'any_order'` → multiset intersection (`Counter &`) as overlap → precision/recall/F1 → `'in_order'` → LCS length drives the same F1. Duplicates are significant in every mode (`['search','search']` ≠ `['search']`).
**Invariant:** The empty-vs-empty = 1.0 rule applies ONLY when both sides are empty — one-sided empty scores 0.0 through the F1 zero-denominator guards (`_f1` returns 0.0 on p+r==0). `exact` mode deliberately bypasses F1 entirely so a mismatch is binary even for near-misses. Rolling DP keeps LCS O(len·len) time, O(len) space — port the 1-D version if trajectories can be long.
**Probe:** `tests/evals/test_agentic_evaluators.py` — `test_tool_spans_v2_and_v3_both_detected_in_start_order` pins ordering; `test_failed_attempts_included_when_requested` (:261-286) pins include_failed interaction with exact mode; suite covers all three orders incl. duplicate significance and empty cases (56 tests).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-pydantic-ai","query":"TrajectoryMatch evaluate","limit":3,"detail":"compact"}'
```
Live check this pass: rank-1 line-exact `agentic.py 324-366`.

## Verdict
Adopt all three modes with their edge-case table — they are pure functions over string lists. Adapt the reason-string format to your report renderer. Omit nothing. Direct tests executed GREEN at pin.
