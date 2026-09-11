<!-- capsule-v2 -->
# Argument validation honesty — why must a negative limit never be echoed back as truth?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What does the #1511 pair teach about numeric argument handling?

## Clamp-or-default + schema-declared minimum
**Path/Symbol:** `src/mcp/mcp.c` search_code handler + tests/test_mcp.c:4271 (`tool_search_code_negative_limit_is_not_echoed_issue1511`), 4285 (`tool_search_code_limit_declares_a_minimum_issue1511`).
**Signature:** limit arg parsed via cbm_get_int_arg → invalid/absent ⇒ schema minimum (never echo raw).
**Data Shape:** limit:-5 must NOT produce "results: -5"; tools/list inputSchema for search_code declares a MINIMUM so agents learn the floor from metadata, not error messages.

### Decisive source
```c
ASSERT_NULL(strstr(resp, "results: -5"));
...
/* tools/list inputSchema carries "minimum" for limit */
```

**Flow:** parse → validate against declared bounds → clamp/default on violation → emit; schema and runtime agree because both derive from one constant.
**Invariant:** Never echo an unvalidated numeric back into output — it teaches agents to send garbage; declare bounds in the schema so planning happens client-side.
**Probe:** the two named tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_mcp_get_int_arg", limit: 5 });
```

## Verdict
Adopt schema-runtime agreement for numeric bounds; adapt limits; add a not-echoed test whenever you accept signed ints.
