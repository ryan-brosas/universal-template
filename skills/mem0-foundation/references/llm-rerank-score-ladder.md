<!-- capsule-v2 -->
# LLM reranker score extraction ladder — decimal-first regex, hard clamp, neutral 0.5 floor

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** how is a numeric relevance score pulled out of free-form LLM text without letting chatty or out-of-range responses corrupt the ranking?

## Connected graph-selected seam
**Path/Symbol:** `mem0/reranker/llm_reranker.py`: `LLMReranker._extract_score` (:135-148); constants `_MAX_INPUT_LEN = 4000` (:133) and `_SYSTEM_PROMPT` (:117-131).
**Signature:** `_extract_score(self, response_text: str) -> float`.
**Data Shape:** raw LLM completion text in; float in [0.0, 1.0] out — never raises on garbage.

### Decisive source
```python
# Prefer a decimal, fall back to an integer, then clamp: out-of-range outputs
# like "2.0"/"5" become 1.0 instead of being mis-parsed into a stray 0/1 digit.
matches = re.findall(r'-?\d+\.\d+', response_text) or re.findall(r'-?\d+', response_text)

if matches:
    score = float(matches[0])
    return min(max(score, 0.0), 1.0)  # Clamp between 0.0 and 1.0

# Fallback: return 0.5 if no valid score found
return 0.5
```

**Flow:** decimal-regex sweep first (so `"I'd say 0.85 relevance (#1)"` yields 0.85, not the stray integer `1`) → integer fallback only if no decimal exists → FIRST match wins → clamp to [0.0, 1.0] → no match at all ⇒ neutral 0.5.
**Invariant:** three failure classes are each handled and must stay ordered: (1) int-first parsing turns explanation digits into scores ("0.85 … #1" → 0); (2) unclamped outputs let "2.0" or "5" dominate every honest doc after sorting; (3) raising on empty output would crash the whole rerank instead of degrading one doc. The per-doc caller (:123-141) additionally truncates query AND document to `_MAX_INPUT_LEN = 4000` before sending, separating system instructions from user data so documents cannot override the scoring prompt.
**Probe:** `grep -cF "re.findall(r'-?\\d+\\.\\d+', response_text)" mem0/reranker/llm_reranker.py` (=1); `grep -cF 'return min(max(score, 0.0), 1.0)' mem0/reranker/llm_reranker.py` (=1); `grep -cF '_MAX_INPUT_LEN = 4000' mem0/reranker/llm_reranker.py` (=1).
**Probe (direct test):** `tests/rerankers/test_llm_reranker_rerank.py` pins the whole ladder — `test_decimal_score_preferred_over_leading_integer` (:43, "Confidence 100%. Relevance: 0.1" → 0.1), `test_out_of_range_scores_are_clamped` (:40), `test_clamps_to_1` (:27), `test_no_score_returns_fallback` (:24).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "_extract_score clamp findall reranker", limit: 10 });
```

## Verdict
Adopt the exact ladder (decimal-first → int → clamp → 0.5) for any LLM-as-judge scorer; adapt the prompt text and input-length cap to your model; omit any "smarter" parsing (JSON mode, last-number-wins) that breaks the documented ordering.
