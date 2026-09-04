<!-- capsule-v2 -->
# Ignore-file precedence — can .cbmignore negation re-include a directory the built-ins skipped, and where is the line?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What is the exact evaluation order across skip-lists, gitignore, global ignore, local ignore, and .cbmignore — including the non-negotiable core?

## Signed match-result ladder with safety-core veto
**Path/Symbol:** `src/discover/discover.c:should_skip_directory` (603–639) + `is_safety_core_dir` (559–563) + signed matcher `src/discover/gitignore.c:cbm_gitignore_match_result` (371–398).
**Signature:** `int cbm_gitignore_match_result(const cbm_gitignore_t *gi, const char *rel_path, bool is_dir);` — returns +1 ignored, −1 negated (last match wins), 0 no match.
**Data Shape:** Safety core = {".git", "node_modules", ".worktrees", ".claude-worktrees"} — NEVER un-skippable. Root `.cbmignore` only (nested files not read); local/global ignores evaluated with path re-basing.

### Decisive source
```c
if (cbm_should_skip_dir(entry_name, mode)) {
    /* #500: a .cbmignore negation ("!obj/") whose rule is the LAST match
     * un-skips a built-in skip-list dir — except the non-negatable safety
     * core. Fall through so .gitignore rules still apply to the un-skipped dir. */
    bool unskipped = cbmignore && !is_safety_core_dir(entry_name) &&
                     cbm_gitignore_match_result(cbmignore, rel_path, true) < 0;
    if (!unskipped) return true;
}
...
int cbm_result = cbm_gitignore_match_result(cbmignore, rel_path, true);
if (cbm_result < 0 && global_ignored) return false;   /* cbmignore un-ignores global */
```

**Flow:** builtin/mode skip-lists → .cbmignore negation may un-skip (except safety core) → repo gitignore → local anchored ignore (path rebased under its dir) → global ignore, with .cbmignore's last-match able to negate a global hit → final verdict.
**Invariant:** The signed tri-state (+/−/0) with LAST-match-wins is what makes negation composable; a plain boolean matcher cannot express "negated after being ignored".
**Probe:** `tests/test_discover.c:discover_cbmignore_negates_always_skip_dir`, `discover_cbmignore_negation_cannot_unskip_safety_core`, `discover_cbmignore_negates_global_ignore`; pattern grammar in tests/test_gitignore.c (`gi_double_star_*`, `gi_negation`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "should_skip_directory", limit: 5 });
```

## Verdict
Adopt signed-match composition and an inviolable safety core for any ignore stack; adapt the core list to your runtime; omit userconfig extension mapping unless you need per-repo language overrides.
