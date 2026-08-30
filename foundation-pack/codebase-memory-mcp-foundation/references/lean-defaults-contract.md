<!-- capsule-v2 -->
# Lean defaults contract — why must the schema never advertise a field the server refuses to emit?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What two "lean default" guards keep agent context small and non-lying?

## Schema-blocklist coherence + verbose-gated git block
**Path/Symbol:** `src/mcp/mcp.c` schema/status handlers + tests/test_mcp.c:2276 (`tool_lean_defaults_schema_and_status`), 2418 (`tool_output_regression_gate`).
**Signature:** get_graph_schema filters advertised properties through the SAME sg_field_blocked list the emitter enforces; index_status omits git-context unless `verbose:true`.
**Data Shape:** Node carrying properties {"fp","sp","bt","complexity"}: schema lists complexity, NEVER fp/sp/bt (they're blocked at emission — advertising them invites unwinnable requests). Status: no worktree/shadow-path block by default.

### Decisive source
```c
/* 1. get_graph_schema must not advertise the blocked internal fields
 *    (fp/sp/bt) — the server refuses to emit them, so listing them in the
 *    schema invited agents to request fields they can never get. */
ASSERT_NOT_NULL(strstr(inner, "complexity")); /* obtainable property listed */
ASSERT_NULL(strstr(inner, "\"fp\""));          /* blocked fields not advertised */
```

**Flow:** emission blocklist is single-source → schema builder consults it too → verbose flag gates diagnostic blocks.
**Invariant:** Advertised surface ⊆ emittable surface — otherwise every response is a lie; defaults should serve the common query, diagnostics opt-in.
**Probe:** `tests/test_mcp.c:tool_lean_defaults_schema_and_status`, `tool_output_regression_gate`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "lean", limit: 5 });
```

## Verdict
Adopt advertise-what-you-emit coherence and opt-in verbosity for any API serving agents; adapt field lists; regression-gate total output sizes.
