<!-- capsule-v2 -->
# File-pattern search semantics — why is a file filter a SUBSTRING match, not a glob?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What does `file_pattern="auth"` match, and what issue pinned the behavior?

## Substring LIKE on file_path (issue #200)
**Path/Symbol:** tests/test_store_search.c:148 (`store_search_by_file_pattern`), 167 (`store_search_file_pattern_substring_issue200`).
**Signature:** params->file_pattern in cbm_store_search.
**Data Shape:** Pattern matches anywhere in file_path via LIKE '%pat%' — so "auth" hits `src/auth/service.go` AND `auth_utils.py`; empty string ignored entirely.

### Decisive source
```c
TEST(store_search_by_file_pattern) { ... }
TEST(store_search_file_pattern_substring_issue200) { ... }
```

**Flow:** append `AND n.file_path LIKE '%'||?||'%'` arm → combine with label/name filters.
**Invariant:** Substring semantics are CONTRACTUAL (#200) — callers wanting extension filtering pass ".go" style patterns; changing to strict globs would break every existing caller.
**Probe:** the two named tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "file_pattern", limit: 5 });
```

## Verdict
Adopt substring file filters with documented semantics; adapt if you need real globs (add a second param rather than changing meaning).
