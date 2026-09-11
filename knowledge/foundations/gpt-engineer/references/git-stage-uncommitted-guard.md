<!-- capsule-v2 -->
# git-stage-uncommitted-guard — How does the tool avoid destroying user work when overwriting files?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** What is the pre-overwrite git safety dance and its exact conditions?

## Git safety seam
**Path/Symbol:** `gpt_engineer/core/git.py:stage_uncommitted_to_git` (:71-85) with helpers is_git_installed/:10, is_git_repo/:14, init_git_repo/:26, filter_files_with_uncommitted_changes/:41, stage_files/:54, filter_by_gitignore/:58.
**Signature:** `stage_uncommitted_to_git(path, files_dict: FilesDict, improve_mode: bool) -> None`.
**Data Shape:** Pure subprocess orchestration; no exceptions — missing git silently skips all protection.

### Decisive source
```python
def stage_uncommitted_to_git(path, files_dict, improve_mode):
    # Check if there's a git repo and verify that there aren't any uncommitted changes
    if is_git_installed() and not improve_mode:
        if not is_git_repo(path):
            print("\nInitializing an empty git repository")
            init_git_repo(path)
    if is_git_repo(path):
        modified_files = filter_files_with_uncommitted_changes(path, files_dict)  # git diff --name-only ∩ files_dict keys
        if modified_files:
            print("Staging the following uncommitted files before overwriting: ", ", ".join(modified_files))
            stage_files(path, modified_files)                                     # git add <those>
```

**Flow:** (gen mode only) ensure repo exists by INITIALIZING one → intersect dirty tracked files (git diff --name-only) with the about-to-be-written FilesDict keys → `git add` just those → subsequent files.push() overwrites, user diff recoverable via staged blobs.
**Invariant:** (1) Auto-init happens ONLY in generate mode (`not improve_mode`) — improving someone's existing project must not create repos behind their back. (2) Staging scope = intersection with files_dict: unrelated dirty files stay untouched (test_filter_by_uncommitted_changes_ignore_staged_files / _ignore_untracked pin the diff --name-only semantics: staged-but-clean and untracked files excluded). (3) Whole chain is best-effort: git absent ⇒ zero protection, silently — acceptable because FileStore.push is plain overwrite otherwise too. (4) has_uncommitted_changes (exit-code probe of git diff --exit-code) exists for callers wanting a boolean gate; the staging path uses name-listing instead. (5) filter_by_gitignore feeds stdin to `git check-ignore --no-index --stdin` — usable in non-repo dirs too (--no-index).
**Probe:** `grep -n 'not improve_mode' gpt_engineer/core/git.py` → :73 (auto-init condition).
**Probe:** `grep -c 'check-ignore' gpt_engineer/core/git.py` → 2 (:60 subprocess argv, :67 explanatory comment).
**Probe:** `tests/core/test_git.py::test_filter_by_uncommitted_changes_ignore_staged_files` proves staged files don't count as dirty here.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "stage_uncommitted_to_git filter_files_with_uncommitted_changes stage_files", limit: 10 });
```

## Verdict
Adopt intersect-then-stage as minimal undoability for file-writing agents; adapt to your VCS; NEVER drop the improve-mode auto-init carve-out — it is the difference between helpful and invasive. Called once in main.py:548 BEFORE files.push(files_dict).
