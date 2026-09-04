<!-- capsule-v2 -->
# similarity-count-ratio — What does "the same line" mean when validating LLM diffs?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** What is the exact line-similarity metric, its normalization, and edge-case semantics?

## Similarity metric seam
**Path/Symbol:** `gpt_engineer/core/diff.py:is_similar` (:381-398) and `count_ratio` (:401-419).
**Signature:** `is_similar(str1, str2, similarity_threshold=0.9) -> bool`; `count_ratio(str1, str2) -> float`.
**Data Shape:** Multiset (Counter) character overlap normalized by LONGER string length after space-stripping lowercasing.

### Decisive source
```python
def count_ratio(str1, str2) -> float:
    str1, str2 = str1.replace(" ", "").lower(), str2.replace(" ", "").lower()
    counter1, counter2 = Counter(str1), Counter(str2)
    intersection = sum((counter1 & counter2).values())
    longer_length = max(len(str1), len(str2))
    if longer_length == 0: return 1
    return intersection / longer_length
```

**Flow:** normalize (drop spaces, lowercase) → multiset intersect → divide by longer length → compare to 0.9.
**Invariant:** (1) ORDER-INSENSITIVE: `"abc"` vs `"cab"` scores 1.0 — this is intentional tolerance for reordered characters, NOT edit distance; two permutations of identical chars always match. (2) Asymmetric penalty: ratio divides by the LONGER side, so appending junk to one string dilutes toward 0 but shortening does not overshoot; empty-vs-nonempty = 0.0, empty-vs-empty = 1.0. (3) Whitespace-insensitivity means indentation changes NEVER break anchors — critical because the file renderer (`FilesDict.to_chat()`) prefixes line numbers and models often mangle leading spaces. (4) Threshold 0.9 is the single knob; find_start_line and validate_lines share it via default arg. (5) Counter `&` keeps MINIMUM counts — duplicated chars in one string don't inflate matches.
**Probe:** execute upstream expectations directly:
```bash
cd <repo> && python3 - <<'EOF'
import sys; sys.path.insert(0, '.')
try:
    from gpt_engineer.core.diff import is_similar
    assert is_similar("abc","cab") and not is_similar("abc","def")
    assert is_similar("A b C","c a b") and not is_similar("Abc","D e F")
    assert is_similar("aabbc","bacba") and not is_similar("aabbcc","abbcc")
    assert not is_similar("","a") and is_similar("a","a")
    print("similarity GREEN")
except ImportError as e:
    print("deps missing:", e)
EOF
```
**Probe:** `tests/core/test_chat_to_files.py:178-199` (test_basic_similarity … test_edge_cases) are the canonical four assertions above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "is_similar count_ratio Counter similarity_threshold", limit: 10 });
```

## Verdict
Adopt count_ratio unchanged wherever LLM text must be matched to source lines (cheap, deterministic, unicode-safe-ish); adapt threshold only with test corpus revalidation; consider omitting for security-sensitive identity checks — permutation tolerance is too loose there.
