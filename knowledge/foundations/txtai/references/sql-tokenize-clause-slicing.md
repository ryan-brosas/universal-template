<!-- capsule-v2 -->
# shlex clause slicing — tokenizing txtai-SQL without a grammar library

**Source:** txtai Apache-2.0 `master@a10667a1c2a4721ce719f3648bd1aeedd03dd84a` (9.13.0); Codebase Memory `txtai`. **Question:** How are clauses located and sliced from a flat token stream when keywords like `order by` span two tokens?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/database/sql/base.py:SQL.tokenize` (:121-150), `.parse` (:152-183); clause table `SQL.CLAUSES` (:17).
**Signature:** `tokenize(query) -> (tokens, positions)`; `parse(tokens, positions, name, offset=1, alias=False, aliases=None, similar=None) -> str|None`.
**Data Shape:** `CLAUSES = ["select", "from", "where", "group", "having", "order", "limit", "offset"]`; `positions` maps keyword → FIRST token index; clause output keys rename `group`→`groupby`, `order`→`orderby`.

### Decisive source
```python
tokens = shlex(StringIO(query), punctuation_chars="=!<>+-*/%|")
tokens.wordchars += ":@#"
tokens.commenters = ""
...
if t not in positions and t in SQL.CLAUSES and (t not in ["group", "order"] or (x + 1 < len(tokens) and tokens[x + 1].lower() == "by")):
    positions[t] = x
```
```python
end = [positions.get(x, len(tokens)) for x in SQL.CLAUSES[SQL.CLAUSES.index(name) + 1 :]]
end = min(end) if end else len(tokens)
clause = tokens[positions[name] + offset : end]
```

**Flow:** lexer splits operator punctuation (`=!<>+-*/%|`) into standalone tokens so comparisons classify; `:@#` stay word chars (bind params `:name` survive whole); comments disabled; first occurrence of each clause keyword wins, with `group`/`order` validated by a following literal `by`. Slicing runs from `position + offset` (offset=2 skips `by`) to the minimum position of any LATER clause keyword — so clause order in CLAUSES is the disambiguation rule.

**Invariant:** Only `select` is parsed with `alias=True` and only `where` collects `similar` (call sites at base.py:55-63); missing clauses yield `None`, never empty string. A clause keyword appearing inside a literal earlier in the query does NOT claim the position (first-match favors earliest), which is why `testUpper`'s uppercase WHERE still resolves and why `"where order by"` mis-slices into a SQLError downstream rather than silently swapping clauses.

**Probe:** `test/python/testdatabase/testsql.py:testUpper` (:296-302), `testLimit`/`testOffset` (:169-186), `testBadSQL` (:73-88 — `where order by` raises SQLError via db.search).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "txtai", query: "tokenize shlex clause positions group by order by punctuation", limit: 10, fields: ["signature", "name", "file"] });
```
Executed live at pin: `SQL.tokenize :121-150` ranked in tier 1 alongside the other repo-wide `tokenize` methods.

## Verdict
Adopt punctuation-as-tokens lexing + positional clause slicing + two-token keyword validation; adapt the CLAUSES table if your virtual-table dialect adds clauses; omit comment handling and quoted-keyword disambiguation (txtai accepts those limits). Coverage: cited paths no_recorded_issue @ gen 2026-08-25T20:20:01Z.
