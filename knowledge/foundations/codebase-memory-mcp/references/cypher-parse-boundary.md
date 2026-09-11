<!-- capsule-v2 -->
# Cypher parser safety — how do you accept a query language without eval-shaped injection risk?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** Where is the parse boundary and what input classes are rejected before SQL generation?

## Strict lexer/parser → AST → parameterized SQL
**Path/Symbol:** `src/cypher/cypher.c` (parser core) + `cypher.h` AST types + tests/test_cypher.c:1219+ (property coalesce queries) and security suite pins.
**Signature:** `int cbm_cypher_parse(const char *text, cbm_cypher_ast_t **out);`
**Data Shape:** Accepts MATCH/WHERE/RETURN/OPTIONAL/ORDER BY/LIMIT subset with property maps, labels, relationship patterns; rejects non-Cypher syntax (including ATTACH attempts — see authorizer capsule); all literals become bound parameters in the emitted SQL.

### Decisive source
```c
/* Parser produces a typed AST; codegen emits parameterized SQL only.
 * Non-Cypher syntax fails at parse — defense-in-depth with the store
 * authorizer which denies ATTACH regardless. */
```

**Flow:** tokenize (string/comment aware) → recursive-descent parse into AST nodes → validate semantics (known functions like coalesce) → generate SQL with placeholders → execute under deadline.
**Invariant:** No user text may reach SQL as raw string interpolation; unknown syntax must FAIL CLOSED at parse, never degrade to substring matching.
**Probe:** tests/test_security.c:`sqlite_blocks_attach_via_cypher`, plus cypher suite property/coalesce cases.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_cypher_parse", limit: 5 });
```

## Verdict
Adopt typed-AST + parameterized-codegen for any embedded query language; adapt grammar; layer with engine-level denies.
