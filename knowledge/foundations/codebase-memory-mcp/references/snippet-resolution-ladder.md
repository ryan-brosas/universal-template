<!-- capsule-v2 -->
# Snippet resolution ladder — how does a bare function name find code without lying about how it matched?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What's the exact→suffix→short-name→fuzzy ladder, and what must each tier disclose?

## Four-tier resolution with match_method disclosure
**Path/Symbol:** `src/mcp/mcp.c` snippet resolver + tests/test_mcp.c:7962–8189 (exact_qn, qn_suffix, unique_short_name, name_tier, ambiguous_short_name, fuzzy_suggestions, fuzzy_last_segment, auto_resolve_default/enabled).
**Signature:** get_code_snippet(qualified_name) → tries: exact QN → QN suffix → unique short name → fuzzy.
**Data Shape:** Exact ⇒ NO match_method field at all. Suffix ⇒ `"match_method":"suffix"`. Ambiguous short name ⇒ error listing candidates; fuzzy miss ⇒ suggestions array. Response carries callers/callees counts; NO signature/return_type spill (source IS the payload — metrics live behind search_graph fields).

### Decisive source
```c
/* Exact match should NOT have match_method */
ASSERT_NULL(strstr(resp, "\"match_method\""));
...
/* suffix tier */
ASSERT_NOT_NULL(strstr(resp, "\"match_method\":\"suffix\""));
/* No property-blob spill: the source IS the payload ... */
ASSERT_NULL(strstr(resp, "\"signature\""));
```

**Flow:** resolve through tiers → ambiguity aborts with candidate list → read source lines → emit with provenance + degree counts.
**Invariant:** Match confidence must be VISIBLE per response (agents calibrate trust); property blobs stay out of snippet payloads to protect context budgets.
**Probe:** the eight named tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "match_method", limit: 5 });
```

## Verdict
Adopt disclosed-tier resolution for any name→artifact lookup; adapt tiers; keep ambiguity errors actionable (list the candidates).
