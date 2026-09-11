<!-- capsule-v2 -->
# Select alias generation — how `where myid != 3` can reference a SELECT alias

**Source:** txtai Apache-2.0 `master@a10667a1c2a4721ce719f3648bd1aeedd03dd84a` (9.13.0); Codebase Memory `txtai`. **Question:** How does the parser know a where-clause name is a user alias that must NOT be resolved to a JSON column?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/database/sql/expression.py:Expression.alias` (:326-353), `.buildalias` (:167-208), `.resolve` (:397-413); gate `src/python/txtai/database/sql/token.py:Token.isalias` (:48-72).
**Signature:** `alias(iterator, tokens, x, aliases, index)`; `resolve(token, aliases) -> str`; `aliases: {normalized_alias: clause_index}`.
**Data Shape:** implicit aliases (`select a a1`, `select a 'a1'`) and explicit `as` both register; values are select-clause positions, so buildalias can skip exactly those expressions.

### Decisive source
```python
# Check for alias or bind parameter
if (aliases and Token.normalize(token) in aliases) or (token.startswith(":")):
    return token
return self.resolver(token)
```
```python
for x, token in enumerate(transformed):
    if x not in aliases.values():
        ...
        token = self.resolver(token, alias)
expression.append(token)
```

**Flow:** only the select clause parses with `alias=True`; when `isalias` fires (prior token is not separator/group-start/distinct AND current token is a column or quoted), `alias()` consumes to the next comma and registers `normalize(alias) → index`. Every later resolve in ANY clause first checks that registry plus the `:` bind-parameter prefix and passes such tokens through untouched. Finally buildalias pairs transformed/original lists POSITIONALLY: for each non-alias position it derives the display alias (stripping surrounding brackets and a leading distinct keyword) and calls `resolver(token, alias)` → e.g. `json_extract(data, '$.a') as "a"`.

**Invariant:** Alias suppression is keyed on NORMALIZED names (lowercase, quotes stripped), which is why `select txt T ... where t LIKE ...` keeps `t` unresolved while `json_extract(...)` still resolves elsewhere. Two failure modes are pinned as SQLError: stray commas producing an empty expression (:189-191) and trailing `as` with no name exhausting the stream (:344-346). A porter who resolves before registering aliases silently breaks every aliased query.

**Probe:** `test/python/testdatabase/testsql.py:testAlias` (:44-71 — all four alias spellings, `myid` reused unresolved in where/groupby/orderby) and `testUnterminated` (:285-294 — stray comma + trailing AS cases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "txtai", query: "alias buildalias suppress resolver empty expression missing alias name", limit: 10, fields: ["signature", "name", "file"] });
```
Executed live at pin: top hits `Expression.alias :326-353`, `Expression.buildalias :167-208`, `testAlias :44-71`.

## Verdict
Adopt register-then-suppress ordering + normalized-name keys + positional alias pairing; adapt alias quoting style per backend; omit SQL-engine-side alias scoping (txtai implements cross-clause alias reuse entirely in the parser because engines like SQLite don't allow WHERE referencing SELECT aliases). Coverage: cited paths no_recorded_issue @ gen 2026-08-25T20:20:01Z.
