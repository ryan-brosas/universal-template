<!-- capsule-v2 -->
# Git-backed undo — revert only the last aider commit, never a pushed or dirty state

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** How does a harness let the user retract the AI's most recent edit without risking an unrelated or pushed commit?

## Scoped undo via tracked commit lineage
**Path/Symbol:** `aider/commands.py`: `Commands.cmd_undo(args)` (:553), `raw_cmd_undo(args)` (:560-655); relies on `Coder.aider_commit_hashes` and the dirty-baseline invariants in `git-safety.md`.
**Signature:** `raw_cmd_undo(self, args) -> None`.
**Data Shape:** only the most recent commit, identified by short SHA, is undble; the commit must (a) be in `aider_commit_hashes`, (b) have exactly one parent, (c) touch only clean, previously-existing files, and (d) be unpushed; it then restores those files from `HEAD~1` and `reset --soft`.

### Decisive source
```python
if last_commit_hash not in self.coder.aider_commit_hashes:
    self.io.tool_error("The last commit was not made by aider in this chat session.")
    return  # never undo a commit aider did not author in this session
...
# every changed file must be clean and pre-existing
for fname in changed_files_last_commit:
    if self.coder.repo.repo.is_dirty(path=fname):
        self.io.tool_error("...uncommitted changes. Please stash them before undoing."); return
    try: prev_commit.tree[fname]
    except KeyError: self.io.tool_error("...not in the repository in the previous commit."); return
...
if has_origin and local_head == remote_head:
    self.io.tool_error("The last commit has already been pushed. Undoing is not possible."); return
...
for file_path in changed_files_last_commit:
    self.coder.repo.repo.git.checkout("HEAD~1", file_path)   # restore only last-commit files
self.coder.repo.repo.git.reset("--soft", "HEAD~1")            # drop the commit, keep worktree
```

**Flow:** require a repo and a head commit with a parent; reject non-aider or multi-parent commits; for every file in the last commit reject dirty/unpin files; reject if pushed to origin; restore exactly those files from `HEAD~1`, aborting outright if any restore fails; then `reset --soft HEAD~1` and report the old/new SHAs.
**Invariant:** undo is scoped to the last aider-owned, single-parent, unpushed commit; it never reverts a pushed commit, a dirty working tree, or a file that did not exist in the prior commit; partial restores abort rather than leaving the repo half-rewound.
**Probe:** `tests/basic/test_commands.py::test_cmd_undo_with_first_commit` (:1260) rejects a first commit; `test_cmd_undo_with_newly_committed_file` (:1224) restores an added file; `test_cmd_undo_with_dirty_files_not_in_last_commit` (:1176) refuses when unrelated working-tree changes exist.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "raw_cmd_undo aider_commit_hashes reset soft checkout HEAD~1", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt a tracked-commit-lineage undo that refuses any non-aider, merged, pushed, dirty, or absent-in-prior history surface. Adapt the commit-authority set and branch/remote layout to the host; keep the restore-then-soft-reset ordering as the safety contract.
