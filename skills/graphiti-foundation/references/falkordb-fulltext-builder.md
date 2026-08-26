<!-- capsule-v2 -->
# FalkorDB fulltext builder — fail-closed query construction

**Source:** graphiti MIT `main@401c59a6`; Codebase Memory `graphiti`. **Question:** when a user query or group-id filter can't be represented safely in RediSearch fulltext syntax, should the builder truncate, escape-loosely, or refuse — and how exactly does it refuse?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/driver/falkordb/fulltext.py:build_falkor_fulltext_query` (:58–83), `sanitize_falkor_fulltext_query` (:48–50), `_escape_fulltext_group_id` (:53–55); consumers re-export it as `_build_falkor_fulltext_query` in `driver/falkordb/operations/search_ops.py`.
**Signature:** `build_falkor_fulltext_query(query: str, group_ids: list[str] | None = None, max_query_length: int = 128) -> str`.
**Data Shape:** input free-text query + optional group ids; output a RediSearch query string of the form `(@group_id:"g1"|"g2") (word1 | word2)` — or the **empty string**, which is this module's "refuse" signal (callers must treat '' as no-results, not wildcard-all).

### Decisive source
```python
def build_falkor_fulltext_query(query, group_ids=None, max_query_length=MAX_QUERY_LENGTH):
    validate_group_ids(group_ids)
    group_filter = ''
    if group_ids:
        escaped_group_ids = [f'"{_escape_fulltext_group_id(g)}"' for g in group_ids]
        group_filter = f'(@group_id:{"|".join(escaped_group_ids)})'
    filtered_words = [w for w in sanitize_falkor_fulltext_query(query).split()
                      if w.lower() not in STOPWORDS]
    if not filtered_words:
        return ''
    sanitized_query = ' | '.join(filtered_words)
    if len(sanitized_query.split(' ')) + len(group_ids or []) >= max_query_length:
        return ''
    return f'{group_filter} ({sanitized_query})'
```

**Flow:** validate group ids → separator-translate every RediSearch special char to space (`str.maketrans` over ~28 chars incl. `-`, `'`, `"`, `:`) and whitespace-collapse → drop stopwords → OR-join words → **if word-count + group-count ≥ 128 return ''** → prefix group filter.
**Invariant:** three distinct refusals all yield `''`: (1) all words are stopwords/separators, (2) the token budget is exceeded — it never truncates mid-query, (3) invalid group ids raise via `validate_group_ids`. A porter who substitutes truncation silently changes security semantics; an empty result set is the contract, a partial match is a vuln. Group ids get char-class escaping `re.sub(r'([^a-zA-Z0-9])', r'\\\1', g)` *inside* double quotes so they can't break out of the filter term.
**Probe:** `tests/utils/search/test_search_security.py:83` backtick-wrapped keyword round-trips; `:93` pure-stopword query returns `''`; `:101` punctuation-only query returns `''`; `:158` default group id builds cleanly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "build_falkor_fulltext_query sanitize STOPWORDS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fail-closed empty-string refusal ladder and the translate-table sanitizer wholesale; adapt the separator set and stopword list to the host engine's tokenizer; omit the FalkorDB-specific `db.idx.fulltext.queryNodes` call syntax if porting to another backend (see dialect-query-dispatch).
