<!-- capsule-v2 -->
# Envelope duplication gate — why must structuredContent NEVER just repeat content[].text?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What property does every tool response satisfy about text vs structured duplication?

## Property test across ALL tools: no payload duplication
**Path/Symbol:** `src/mcp/mcp.c` envelope builders + tests/test_mcp.c:2021 (`mcp_every_tool_result_is_duplication_free`), 2186 (`tool_output_byte_budgets`).
**Signature:** per-tool result → {content:[{text}], structuredContent} — the property: if text parses as a JSON OBJECT, it must NOT be re-embedded in structuredContent (and vice versa); errors keep machine-readable non-empty structure.
**Data Shape:** Error envelopes: wrapped {"error": <text>} or the parsed object — "an empty object is the #1522 lie in error clothing". Byte budgets cap total response sizes per tool.

### Decisive source
```c
/* Errors keep machine-readable structure: either the wrapped {"error": <text>}
 * form, or — when the error payload is itself a JSON object — that object
 * parsed. Non-empty either way; an empty object is the #1522 lie in error
 * clothing. */
```

**Flow:** iterate EVERY registered tool with minimal args (error envelopes included!) → assert the duplication property + budget compliance.
**Invariant:** Duplication doubles agent token cost silently; the property must hold for ERROR envelopes too, which is what makes the loop-over-all-tools design strong.
**Probe:** `tests/test_mcp.c:mcp_every_tool_result_is_duplication_free`, `tool_output_byte_budgets`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "structuredContent", limit: 5 });
```

## Verdict
Adopt whole-catalog property tests for response-shape contracts; adapt to your envelope; never let an error degrade to empty JSON.
