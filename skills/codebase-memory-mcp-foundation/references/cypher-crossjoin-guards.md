<!-- capsule-v2 -->
# Cypher cross-join guards — how do you keep a careless MATCH from materializing a cartesian product?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What static checks bound multi-pattern queries before execution?

## Disconnected-pattern detection + row-budget refusal
**Path/Symbol:** `src/cypher/cypher.c` codegen guards (deadline/guards greps) + tests/test_cypher.c suite.
**Signature:** embedded in `cbm_cypher_execute(s, text, deadline_ms, out)`.
**Data Shape:** Multi-MATCH or comma-separated patterns without connecting variables ⇒ rejected as cartesian risk; estimated row explosion above budget ⇒ refused with guidance to add LIMIT/WHERE; per-loop deadline checks remain the runtime backstop.

### Decisive source
```c
/* Cross-join guard: patterns sharing no variable would emit a cartesian
 * product; refuse at plan time rather than OOM at run time. */
```

**Flow:** parse → analyze pattern graph connectivity → disconnected components ⇒ error naming the variables to connect → connected: estimate fan-out from label counts → over-budget ⇒ suggest constraints → else execute with hot-loop deadline sampling.
**Invariant:** Static refusal must precede dynamic limits — an unbounded product never gets a first row.
**Probe:** cypher suite guard cases; deadline twins in tests/test_cypher.c.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cross_join", limit: 5 });
```

## Verdict
Adopt plan-time connectivity analysis for any user-writable join language; adapt budgets; pair with execution deadlines.
