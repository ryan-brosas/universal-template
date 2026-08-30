<!-- capsule-v2 -->
# Scoped Git safety — dirty baselines and edited-path-only commits

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** How does a harness auto-commit model edits without ever sweeping the user's unrelated dirty files into an AI change?

## Dirty-union baseline and edited-scoped commit
**Path/Symbol:** `aider/repo.py`: `GitRepo.get_dirty_files()` (:581), `is_dirty(path)` (:598), `GitRepo.commit(fnames=None, ..., aider_edits=False)` (:131); `aider/coders/base_coder.py`: `auto_commit(edited, context=...)` (:2375), `dirty_commit()` (:2411), `check_for_dirty_commit(path)` (:2175).
**Signature:** `get_dirty_files() -> list[str]` (staged+unstaged union); `auto_commit(edited) -> str | None`; `dirty_commit() -> bool`.
**Data Shape:** `commit(fnames=edited)` commits exactly the edited path set; a pre-existing dirty baseline is snapshot-committed first so the AI change is individually revertable.

### Decisive source
```python
def get_dirty_files(self):
    dirty_files = set()
    dirty_files.update(self.repo.git.diff("--name-only", "--cached").splitlines())  # staged
    dirty_files.update(self.repo.git.diff("--name-only").splitlines())              # unstaged
    return list(dirty_files)
# auto-commit is scoped to the edited path set only
res = self.repo.commit(fnames=edited, context=context, aider_edits=True, coder=self)
# a dirty baseline is committed BEFORE the edit so /undo reverts only the AI change
def dirty_commit(self):
    if not self.need_commit_before_edits or not self.dirty_commits:
        return
    self.repo.commit(fnames=self.need_commit_before_edits, coder=self)
```

**Flow:** union staged+unstaged dirty files; guard each proposed edit with `is_dirty`; if a target is already dirty, `dirty_commit` first snapshots the baseline; `auto_commit(edited)` commits only the edited paths with a scoped generated message; any Git error is caught and surfaced as `Unable to commit`, never raised.
**Invariant:** staged and unstaged both count as dirty; an auto-commit is scoped to edited paths only; a dirty baseline is committed before the edit so the AI change is individually revertable; the temporary author/committer env is restored even on failure.
**Probe:** `tests/basic/test_coder.py::test_only_commit_gpt_edited_file` (:612) scopes to edited file; `test_gpt_edit_to_dirty_file` (:667) baseline-before-edit; `tests/basic/test_repo.py` covers `diffs_*`, custom committer (:192), `co_authored_by` (:267).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "get_dirty_files auto_commit dirty_commit scoped commit", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt scoped auto-commit (edited paths only) and baseline-before-edit dirty preservation as the safety contract. Adapt to the host: never auto-commit originals or change Git identity by default; keep the scoped-edit guarantees under an explicit user gate.
