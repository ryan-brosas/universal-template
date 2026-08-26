<!-- capsule-v2 -->
# Empty-repo diff selection — "show me the changes" on branches with zero commits or detached HEAD

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How do you compute the working-changes diff when `git diff HEAD` would fail (newborn repo, orphan branch, detached HEAD) — and annotate files git cannot diff yet?

## Probe for any commit first; split index/worktree diffs when there is nothing to diff against
**Path/Symbol:** `aider/repo.py`: `GitRepo.get_diffs(fnames=None)` (:375-417); explicit-range variant `diff_commits(pretty, from_commit, to_commit)` (:419-431).
**Signature:** `get_diffs() -> str` (possibly ""); `diff_commits() -> str`.
**Data Shape:** `current_branch_has_commits: bool` from `any(iter_commits(active_branch))`; TypeError AND ANY_GIT_ERROR both swallowed around the probe (detached HEAD raises on `active_branch`).

### Decisive source
```python
if current_branch_has_commits:
    args = ["HEAD", "--"] + list(fnames)
    diffs += self.repo.git.diff(*args, stdout_as_string=False).decode(self.io.encoding, "replace")
    return diffs

wd_args = ["--"] + list(fnames)
index_args = ["--cached"] + wd_args
diffs += self.repo.git.diff(*index_args, stdout_as_string=False).decode(...)
diffs += self.repo.git.diff(*wd_args, stdout_as_string=False).decode(...)
# earlier, for every requested fname:
if not self.path_in_repo(fname):
    diffs += f"Added {fname}\n"
```

**Flow:** probe branch history (errors => treat as commitless) -> prepend "Added <fname>" annotations for requested-but-untracked paths -> one `git diff HEAD -- paths` when commits exist, else concatenated `git diff --cached --` + `git diff --` -> bytes decoded with `io.encoding` and `errors="replace"`.
**Invariant:** NEVER issue `git diff HEAD` against a commitless branch; untracked-but-requested files are announced, not silently dropped; hostile bytes never raise — they are replacement-decoded; diff failures print "Unable to diff" and yield "" instead of raising.
**Probe:** `tests/basic/test_repo.py` — `test_diffs_empty_repo` (:22), `test_diffs_nonempty_repo` (:39), `test_diffs_with_single_byte_encoding` (:62), `test_diffs_detached_head` (:84), `test_diffs_between_commits` (:114, the diff_commits variant). Executed GREEN this run (repo `.venv`). Anchors: `grep -nF 'current_branch_has_commits' aider/repo.py | head -4` -> :378/:383/:398; `grep -nF '"--cached"' aider/repo.py` -> :406; `grep -nF '--color=never' aider/repo.py` -> :424.
**Coverage caveat:** none — all cited ranges indexed `no_recorded_issue`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "get_diffs", limit: 3 });
// resolves GitRepo.get_diffs :375-417 rank-1
```

## Verdict
Adopt the commit-presence probe plus the index+worktree split as the empty-repo contract, and the "Added" annotation for undiffable paths. Adapt encoding policy and color flags to the host UI; omit Aider's io coupling by parameterizing the decoder.