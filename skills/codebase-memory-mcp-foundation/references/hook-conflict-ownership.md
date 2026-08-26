<!-- capsule-v2 -->
# Hook conflict ownership — how do you uninstall YOUR lifecycle hook without touching a user's hand-written one?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What manifest/ownership rules make hook install/uninstall idempotent and non-destructive across binary changes?

## Canonical-shape manifests + BIN-assignment ownership + stdout notices
**Path/Symbol:** `src/cli/cli.c` hook plane + tests/test_cli.c:4949 (`cli_hook_conflict_emits_stdout_notice_issue1388`), 4975 (`cli_install_preserves_hook_entries_when_scripts_unowned_issue1387`), 8392 (BIN-assignment re-ownership), 8844 (Copilot cross-manifest guard), 9609+ (hook_augment contracts).
**Signature:** install/uninstall flows over vendor hook JSON entries; ownership decided by script-path binding, not by command name.
**Data Shape:** An installed hook entry references an OWNED script path under the tool's private dir; user hooks referencing foreign scripts are preserved verbatim on uninstall; a changed script BIN assignment makes the entry user-owned (no silent reclaim).

### Decisive source
```c
TEST(cli_install_preserves_hook_entries_when_scripts_unowned_issue1387) { ... }
/* changing only a hook script BIN assignment must make it user-owned */
TEST(cli_hook_conflict_emits_stdout_notice_issue1388) { ... }
```

**Flow:** install → write owned script + register entry pointing at it → if an entry with the same event exists but points elsewhere, emit a stdout NOTICE and leave it alone (#1388) → uninstall → remove only entries whose scripts match our owned paths; unowned/foreign entries survive untouched → a manifest must never claim another binary's canonical shape (#8844).
**Invariant:** Ownership follows the SCRIPT file identity; conflicts surface as notices, never as silent overwrites.
**Probe:** the four named tests above plus `cli_special_hook_failures_propagate_from_install_and_uninstall`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "hook", limit: 5 });
```

## Verdict
Adopt script-identity ownership + notice-don't-overwrite for any tool that edits shared agent config; adapt entry schemas; keep the cross-binary manifest guard.
