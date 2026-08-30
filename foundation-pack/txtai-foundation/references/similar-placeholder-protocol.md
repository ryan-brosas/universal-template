<!-- capsule-v2 -->
# similar() placeholder protocol — parser-side half of the temp-table join

**Source:** txtai Apache-2.0 `master@a10667a1c2a4721ce719f3648bd1aeedd03dd84a` (9.13.0); Codebase Memory `txtai`. **Question:** How does a `similar('query', n)` call inside user SQL survive parsing when the actual similarity results only exist after embedding?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/database/sql/expression.py:Expression.similar` (:250-283); consumer `src/python/txtai/database/base.py:Database.search` (:143-164).
**Signature:** `similar(iterator, tokens, x, similar)`; replacement token constant `Token.SIMILAR_TOKEN = "__SIMILAR__"` (token.py:12).
**Data Shape:** `similar` accumulates `[["abc"], ["abc", "1000"], ...]` — quote-stripped parameter strings; the where-clause text keeps literal markers `__SIMILAR__0`, `__SIMILAR__1`, ...

### Decisive source
```python
while token and token != ")":
    x, token = self.readtoken(iterator)
    if token and token not in ["(", ",", ")"]:
        # Strip quotes and accumulate tokens
        params.append(token.replace("'", "").replace('"', ""))
    tokens[x] = None
# Add placeholder for embedding similarity results
tokens[x] = f"{Token.SIMILAR_TOKEN}{len(similar)}"
similar.append(params)
```
```python
for x in range(len(similarity)):
    token = f"{Token.SIMILAR_TOKEN}{x}"
    if where and token in where:
        where = where.replace(token, self.embed(similarity, x))
```

**Flow:** parse time — consume tokens to the closing paren (nested parens are NOT counted here; `(`/`,`/`)` are skipped), strip quotes from every parameter, splice `__SIMILAR__<n>` at the last consumed position, append params. Query time — `Database.search` substitutes each marker with `embed(similarity, x)`, i.e. the batch-temp-table IN-clause documented in `temp-table-similarity-join`.

**Invariant:** Placeholder numbering is APPEND ORDER of similar() calls, not source position — two similar() calls inside one function (`coalesce(similar('a'), similar('b'))`) still get 0/1 in call order. Because substitution is plain TEXT replace on the where string, a marker can never be confused with data: users cannot inject the literal token accidentally in practice since quotes around it would make it a quoted literal. Unbalanced paren → SQLError("Unterminated clause") via readtoken (:415-428).

**Probe:** `test/python/testdatabase/testsql.py:testSimilar` (:234-257 — `where similar('abc')` → `"__SIMILAR__0"`, similar list `[["abc"]]`; `similar('abc', 1000)` → `[["abc", "1000"]]`; coalesce nesting), `testUnterminated` (:281-283).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "txtai", query: "similar placeholder token parameters quotes strip unterminated paren", limit: 10, fields: ["signature", "name", "file"] });
```
Executed live at pin: `Expression.similar :250-283` + `testUnterminated :259-294` + Token predicate family ranked tier 1.

## Verdict
Adopt the two-phase protocol (parse-time placeholder, query-time text substitution into the id clause); adapt the marker format if your clause transport is structured rather than textual; omit paren-nesting inside similar() args (txtai treats them as separators). Pairs with `temp-table-similarity-join`, which covers the RDBMS-side embed/scores half — this capsule is the parser-side emission only. Coverage: cited paths no_recorded_issue @ gen 2026-08-25T20:20:01Z.
