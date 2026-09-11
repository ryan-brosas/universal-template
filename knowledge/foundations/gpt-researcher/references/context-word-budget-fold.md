<!-- capsule-v2 -->
# Context word-budget fold — what exactly does trim_context_to_word_limit keep, truncate, and discard?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** When accumulated deep-research context exceeds 25k words, which items survive the cut?

## Newest-first reverse fold with one oversized-head truncation
**Path/Symbol:** `gpt_researcher/skills/deep_research.py:207-231` (`count_words`, `trim_context_to_word_limit`), applied at `:566` and `:624`.
**Signature:** `def trim_context_to_word_limit(context_list: List[str], max_words: int = MAX_CONTEXT_WORDS) -> List[str]`
**Data Shape:** In/out are ordered context lists (strings or list-likes); MAX_CONTEXT_WORDS=25000 module constant.

### Decisive source
```python
for item in reversed(context_list):        # newest first
    words = count_words(item)
    if total_words + words <= max_words:
        trimmed_context.insert(0, item)    # keep original order
        total_words += words
    elif not trimmed_context:              # FIRST (newest) item alone over budget:
        trimmed_context.insert(0, " ".join(text.split()[:max_words]))  # hard head-truncate
        break
    else:
        break                              # older items dropped WHOLESALE — no partial refill
```

**Flow:** walk from newest → accumulate while under budget → if even the newest item exceeds the whole budget, truncate IT to max_words and stop → otherwise the first over-budget item stops everything; all older items vanish.
**Invariant:** output is a PREFIX of the input in original order (newest window preserved), never a mix of old+new. There is NO partial fill from older items once the budget trips — porters adding "keep fitting small old items" change the semantics. Applied twice: per-descent-level (`:566`) and on the citation-annotated final context (`:624`) before joining into `researcher.context`.
**Probe:** `tests/test_deep_research_parsing.py::test_trim_context_to_word_limit_*` pins both boundary cases; battery B1/B2/B3/B3b executed AST-lifted verbatim GREEN (66/66 run).
