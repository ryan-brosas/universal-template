<!-- capsule-v2 -->
# String request IDs — why must JSON-RPC ids survive as strings, never coerced to numbers?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What breaks when a server strtol's a string id (issue #253)?

## id_str passthrough + has_id flag
**Path/Symbol:** `src/mcp/mcp.c:cbm_jsonrpc_parse/_format_response` + tests/test_mcp.c:712/733 (`jsonrpc_parse_string_id_issue253`, `jsonrpc_format_response_string_id_issue253`).
**Signature:** `int cbm_jsonrpc_parse(const char *line, cbm_jsonrpc_request_t *req);` — req carries `has_id`, `id_str`, numeric twin.
**Data Shape:** `"id":"init-abc"` parses with id_str="init-abc"; `"xyz"` must NOT become 0 under any numeric coercion; responses echo `"id":"init-abc"` VERBATIM — the test asserts `"id":0` is absent.

### Decisive source
```c
/* A purely non-numeric string would have become 0 under strtol. */
ASSERT_STR_EQ(req2.id_str, "xyz");
...
/* issue #253: the response must echo the string id verbatim, not as a number. */
ASSERT_NOT_NULL(strstr(json, "\"id\":\"init-abc\""));
ASSERT_NULL(strstr(json, "\"id\":0"));
```

**Flow:** parse keeps both representations → dispatch correlates by whichever form arrived (see cancellation-scoping capsule for the matching rule) → response formatting picks string form when id_str set.
**Invariant:** Ids are OPAQUE correlation tokens per spec; any normalization breaks clients that match on exact strings.
**Probe:** `tests/test_mcp.c:jsonrpc_parse_string_id_issue253`, `jsonrpc_format_response_string_id_issue253`, `jsonrpc_parse_string_id`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "id_str", limit: 5 });
```

## Verdict
Adopt dual-representation opaque ids in any JSON-RPC implementation; adapt struct; add the verbatim-echo test before your first string-id client appears.
