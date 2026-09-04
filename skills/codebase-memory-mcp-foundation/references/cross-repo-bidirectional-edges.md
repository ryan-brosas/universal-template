<!-- capsule-v2 -->
# Cross-repo bidirectional edges — how do you link caller↔handler across two databases atomically enough to trust?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** When a route match spans source and target project DBs, how are CROSS_* edges written so neither side ends up half-linked?

## Forward-then-reverse with cancel checks and strict validation
**Path/Symbol:** `src/pipeline/pass_cross_repo.c:emit_cross_route_bidirectional` (539–593); identity gate `cr_store_has_exact_project` (123–152).
**Signature:** `static bool emit_cross_route_bidirectional(src_store, src_project, src_db, caller_id, local_route_id, tgt_store, tgt_project, handler_id, route_qn, handler_name, handler_file, url_path, method, edge_type, ctx);`
**Data Shape:** Edge types: CROSS_HTTP_CALLS / CROSS_ASYNC_CALLS / CROSS_CHANNEL. Forward props name the TARGET (handler, file, url_path, method); reverse props name the CALLER. Shadow projects (`<name>::missed`) never count as primaries.

### Decisive source
```c
/* Forward: caller → local Route in source DB */
if (!insert_cross_edge(src_store, src_project, caller_id, local_route_id, edge_type, fwd, ctx))
    return false;
if (cr_cancel_requested(ctx)) return false;
/* Reverse: handler → Route in target DB */
... if ((step_rc != SQLITE_ROW && step_rc != SQLITE_DONE) || finalize_rc != SQLITE_OK ||
        tgt_route_id == 0) return false;
...
/* Only the shadow rows stop counting toward [single-primary]; this is the same
 * defect mcp.c fixed for list_projects in #1044; this site never learned it. */
```

**Flow:** validate each side's store has EXACTLY one primary row matching the project → resolve target Route by QN (strict: zero or failed step ⇒ abort before writing reverse) → write forward edge → check cancellation → resolve handler's local Route id → write reverse edge with mirrored props.
**Invariant:** Never write the reverse leg if forward validation failed — a dangling one-sided cross edge is worse than none; identity must be proven per-DB (count==1 over non-shadow primaries), not assumed from filenames.
**Probe:** `tests/test_cross_repo.c:cross_repo_propagates_delete_failure`, `cross_repo_failed_bidirectional_insert_is_not_counted`, `cross_repo_accepts_project_with_missed_shadow_row_issue1609`, `cross_repo_cancel_mid_run_keeps_completed_target_and_stops_before_later_target`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "emit_cross_route_bidirectional", limit: 5 });
```

## Verdict
Adopt validate-both-sides + ordered writes + cancel checkpoints for any cross-store linkage; adapt props schema; omit gRPC/GraphQL/trpc variants unless you index those protocols too.
