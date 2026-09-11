<!-- capsule-v2 -->
# Hook augment never-deny contract — how do you add lifecycle hooks that can NEVER block a tool call?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What design makes an agent-side hook structurally incapable of denying or stalling a tool?

## Exit-0 pass-through + 300ms hard deadline + bounded cwd walk-up
**Path/Symbol:** `src/cli/hook_augment.c` header contract (1–60), deadline (44–60), `ha_resolve_indexed_project_with_root` (843–884).
**Signature:** reads a vendor hook payload on stdin; emits event-specific context JSON or nothing. Constants: `HA_DEADLINE_MS 300`, `HA_MAX_WALKUP 8`, `HA_MIN_TOKEN 4`, `HA_RESULT_LIMIT 5`.
**Data Shape:** Input = documented vendor hook JSON (`hook_event_name`, `cwd`, ...). Output = `hookSpecificOutput.additionalContext` for SessionStart/SubagentStart, symbol hints for search events; EVERY failure path ⇒ exit 0 with NO stdout.

### Decisive source
```c
/* Cardinal rule: this NEVER blocks a tool call. Every error, timeout, missing
 * project, or short/odd pattern path results in `exit 0` with NO stdout
 * output (a clean pass-through). ... The underlying query is `search_graph`
 * (pure SQLite, shell-free) — chosen over `search_code` (which shells out) */
...
/* A fired deadline is otherwise indistinguishable from "no matches", so the
 * handler first write()s a pre-formatted breadcrumb ... only async-signal-safe
 * write/_exit in the handler. */
```

**Flow:** read capped stdin → arm SIGALRM-style 300ms budget (breadcrumb logged to a private file if it fires) → resolve nearest indexed project by walking up at most 8 dirs probing derived project names via index_status → run search_graph → emit ≤5 result hints once, at the very end (no partial JSON on timeout).
**Invariant:** Output is written exactly ONCE at completion; the deadline handler only write()+_exit(0); short/noisy tokens (<4 chars) bail before any DB work.
**Probe:** `tests/test_cli.c:cli_hook_augment_lifecycle_output_contract` (Session/Subagent context includes tool names, leaks no cwd path, non-lifecycle events return NULL) and `cli_hook_conflict_emits_stdout_notice_issue1388`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "ha_resolve_indexed_project_with_root", limit: 5 });
```

## Verdict
Adopt fail-open exit-0 discipline, single-write emission, and the walk-up project resolution for any agent hook; adapt the vendor payload schema; omit the per-dialect Copilot formatter unless you target it.
