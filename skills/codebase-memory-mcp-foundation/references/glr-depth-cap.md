<!-- capsule-v2 -->
# GLR depth cap — how do you stop a pathological ambiguous parse from overflowing the native stack?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** When tree-sitter's GLR stack merging recurses per nesting level, what bound yields a VALID parse instead of a crash?

## CBM_TS_STACK_MERGE_MAX_DEPTH — leave ambiguity unmerged
**Path/Symbol:** `internal/cbm/ts_runtime` cap `CBM_TS_STACK_MERGE_MAX_DEPTH` + regression tests/test_stack_overflow.c:perl_glr_deep_parse_recursion_capped (617–646).
**Signature:** (runtime-internal) stack_node_add_link merge path honoring the depth env/constant; test drives 30,000-deep `f(f(f(...)))` Perl.
**Data Shape:** Past the bound, the parser leaves ambiguous heads UNMERGED on the GLR stack — a valid parse with deferred ambiguity — instead of recursing further. Complements pre-parse guards (`CBM_PERL_MAX_PARSE_NESTING`) which this input deliberately bypasses.

### Decisive source
```c
/* Perl's paren-optional call grammar makes each level ambiguous, so tree-sitter's
 * GLR parser merges the ambiguous parse-stack heads recursively — stack_node_add_link,
 * once per nesting level — overflowing the native stack during the parse, before any
 * extraction runs. The CBM_TS_STACK_MERGE_MAX_DEPTH cap stops merging past the
 * bound: the ambiguity is left on the GLR stack instead of merged — a valid parse,
 * never a wrong one — so the parse returns cleanly instead of crashing. */
const int DEPTH = 30000;
... ASSERT_FALSE(so_parse_crashes(src, CBM_LANG_PERL));
```

**Flow:** deep ambiguous source → GLR creates one stack head per nesting level → at merge time, if link chain exceeds the cap, skip merging and keep heads → extraction sees a valid (ambiguous) tree → no SIGSEGV even on ~1MB Windows stacks.
**Invariant:** Capping must degrade to "less merged", never to "wrong AST"; the guard is per-parse, not global state.
**Probe:** `tests/test_stack_overflow.c:perl_glr_deep_parse_recursion_capped`; sibling crash-safety pins: `lsp_ts_cyclic_types_no_crash`, `lsp_java_deep_nesting_no_crash`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "stack_merge_depth", limit: 5 });
```

## Verdict
Adopt merge-depth caps for any GLR/backtracking parser you embed; adapt the constant to your minimum supported stack; omit the pre-parse nesting guards where the cap suffices.
