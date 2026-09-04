<!-- capsule-v2 -->
# Empty-pattern search — why does an empty search string mean "no filter" instead of zero results?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you avoid the classic "LIKE '%%' matches nothing useful" trap while keeping empty filters meaningful?

## Empty ⇒ omit arm entirely (label and pattern)
**Path/Symbol:** tests/test_store_search.c:97 (`store_search_empty_label_ignored`), 73 (`store_search_by_name_pattern`).
**Signature:** params->name_pattern / ->label in cbm_store_search.
**Data Shape:** NULL or "" label/pattern arms are OMITTED from the WHERE clause rather than bound; a label-only search returns all nodes of that label; both empty = unfiltered listing (paginated).

### Decisive source
```c
TEST(store_search_empty_label_ignored) { ... }
TEST(store_search_by_name_pattern) { ... }
```

**Flow:** build WHERE incrementally: only append arms for non-empty criteria → always keep unique ORDER + pagination.
**Invariant:** Distinguish "no criterion" (omit) from "criterion that can't match" (e.g., label="NoSuchLabel" still yields a real arm); conflating them breaks list-all use cases.
**Probe:** the two named tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_search", limit: 5 });
```

## Verdict
Adopt omit-empty-arm construction in dynamic SQL builders; adapt defaults; document the distinction in your API docs.
