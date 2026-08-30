<!-- capsule-v2 -->
# Bracket JSON-path expression — `[a[0].b]` as one resolved token

**Source:** txtai Apache-2.0 `master@a10667a1c2a4721ce719f3648bd1aeedd03dd84a` (9.13.0); Codebase Memory `txtai`. **Question:** How can users reference JSON fields with spaces, dots, and array indexes in a whitespace-tokenized SQL dialect?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/database/sql/expression.py:Expression.bracket` (:210-248).
**Signature:** `bracket(iterator, tokens, x)` — consumes from `[`, splices the resolved path at the last consumed position.
**Data Shape:** bracket content is an arbitrary JSON path string (`$.field`, `$.a[0].ab`, names containing spaces or quotes).

### Decisive source
```python
tokens[x] = None
brackets = 1
while token and (token != "]" or brackets > 0):
    x, token = self.readtoken(iterator)
    if token == "[":
        brackets += 1
    elif token == "]":
        brackets -= 1
    ...
# Set last token to resolved bracket expression
tokens[x] = self.resolve(self.buildtext(params).replace("'", "''"), None)
```

**Flow:** null the open-bracket token → consume tokens counting nested `[`/`]` → rebuild content with buildtext (whitespace rules rejoin spaced names like `[ab cd]`) → double single quotes for SQL literal safety → resolve AS ONE TOKEN through the normal resolver (so it lands on `json_extract(data, '$.<path>')`). Because the result is a plain token, brackets compose with everything else: functions (`avg([a])`), distinct, compound expressions.

**Invariant:** Quote-doubling happens at parse time (`'` → `''`), so `[field']` becomes `'$.field'''`; a porter who escapes with backslashes instead breaks SQLite/duckdb literals. Unterminated bracket (no matching `]`) exhausts the iterator → SQLError("Unterminated clause") via readtoken — never a silent partial path.

**Probe:** `test/python/testdatabase/testsql.py:testBracket` (:90-111 — `[a[0].c[0]]`, `[ab cd]`, `[field']` quote doubling, groupby/orderby placement) and `testUnterminated` (:264-272 — three unterminated forms all raise SQLError).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "txtai", query: "bracket expression json path escape single quote resolve token", limit: 10, fields: ["signature", "name", "file"] });
```
Executed live at pin: top hit `Expression.bracket :210-248`, second `Expression.resolve :397-413`.

## Verdict
Adopt bracket-delimited raw paths + quote doubling + single-token resolution; adapt the emitted JSON function per backend via jsoncolumn hooks (see sql-column-resolution-ladder); omit nested-bracket arithmetic — brackets count depth only, they are not expressions. Coverage: cited paths no_recorded_issue @ gen 2026-08-25T20:20:01Z.
