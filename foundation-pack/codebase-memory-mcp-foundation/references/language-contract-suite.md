<!-- capsule-v2 -->
# Language-contract regression suite — how do you pin graph OUTPUT invariants across 60+ languages without golden files?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What test architecture catches real per-language extraction bugs that snippet-level unit tests miss?

## Full-pipeline fixtures + presence floors + forked-crash capture
**Path/Symbol:** `tests/test_lang_contract.c` (design notes 7–27) + edge-family twins tests/test_edge_structural.c (FAMILY sections) + tests/test_edge_types_probe.c.
**Signature:** per-language `TEST(contract_*)` driving the FULL production index flow (`mode=full` so similarity/semantic predump passes run), then asserting on the resulting graph DB.
**Data Shape:** Assertions are INVARIANTS, never golden snapshots: expected node/edge TYPES present, calls attributed to the calling Function (not file/Module), counts as floors (`>=1`). Crashes caught via FORKED subprocess + exit-signal check because ASan does NOT intercept SIGBUS.

### Decisive source
```c
/* Unlike the in-process unit tests ... this suite indexes a per-language
 * fixture through the FULL pipeline into a real graph DB and asserts INVARIANT
 * contracts on the result ...
 *   - INVARIANTS, not golden snapshots: edge counts are non-deterministic
 *     (parallel LSP/similarity/resolve), so we assert PRESENCE + floors ...
 *   - Crashes are caught via a FORKED subprocess + exit-signal check: ASan does
 *     NOT intercept SIGBUS, so an in-process crash would kill the test runner. */
```

**Flow:** write minimal per-language fixture → index through the same entrypoint users hit → query the store for edge types/symbols → assert floors and attribution → histogram dump on failure shows what WAS produced.
**Invariant:** Presence-floors survive grammar refreshes without churn; crash isolation must be external to the process under test.
**Probe:** `tests/test_lang_contract.c:contract_c_calls_attributed_to_function`, `contract_edge_handles`, `contract_edge_similar_to`, `contract_kotlin_imports_extracted`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "lang_contract", limit: 5 });
```

## Verdict
Adopt full-pipeline invariant suites alongside unit tests for any multi-backend extractor; adapt fixture set; the fork-isolation pattern is mandatory wherever SIGBUS is possible.
