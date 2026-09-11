<!-- capsule-v2 -->
# Source lossy-UTF8 — how do you serve source code that contains invalid bytes without breaking JSON?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What's the sanitize policy for file contents on the way into a JSON envelope?

## Lossy replacement (U+FFFD), structure preserved, response still valid JSON
**Path/Symbol:** `src/mcp/mcp.c` snippet source reader + tests/test_mcp.c:8258 (`snippet_source_invalid_utf8`).
**Signature:** internal sanitize between file read and envelope write.
**Data Shape:** Fixture embeds raw invalid bytes 0xC0 0xD4 0xB7 0xC2 mid-function. Response: valid JSON, original identifiers/keywords intact ("HandleRequest", "return nil" present), bad byte run replaced (replacement char detectable), raw sequence ABSENT.

### Decisive source
```c
const unsigned char source[] = { ..., 0xC0, 0xD4, 0xB7, 0xC2, ... };
ASSERT_TRUE(is_valid_json_response(raw));
ASSERT_NULL(strstr(resp, "\xC0\xD4"));
ASSERT_TRUE(snippet_source_has_replacement(resp));
```

**Flow:** read bytes → validate UTF-8 → replace invalid sequences with U+FFFD → escape per JSON rules → emit.
**Invariant:** Never reject the whole snippet over encoding — real repos contain Latin-1 comments and mixed encodings; degrade to replacement, keep line structure.
**Probe:** `tests/test_mcp.c:snippet_source_invalid_utf8` plus search_code utf8 twins at 4368–4616.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "utf8", limit: 5 });
```

## Verdict
Adopt lossy-with-structure sanitization for any user-content channel; adapt replacement policy; test with hand-built invalid byte runs, not just clean fixtures.
