<!-- capsule-v2 -->
# File-add admission machine — what ordered gates decide whether `/add word` may touch coder state?

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How does a chat harness admit user-named files into editable context without letting globs smuggle untracked files or read-only files silently become writable?

## Two-stage admission: word resolution, then per-file consent gates
**Path/Symbol:** `aider/commands.py`: `Commands.cmd_add` (:799-903), `Commands.glob_filtered_to_repo` (:765-797).
**Signature:** `cmd_add(self, args)`; `glob_filtered_to_repo(self, pattern) -> list[str]` (repo-relative strings).
**Data Shape:** mutates `coder.abs_fnames` (set) and `coder.abs_read_only_fnames` (set); refusals print via io.tool_error/warning and `continue`, never raise.

### Decisive source
```python
# glob expansion is TRACKED-file-filtered: globs can never add untracked files
if self.coder.repo:
    git_files = self.coder.repo.get_tracked_files()
    matched_files = [fn for fn in matched_files if str(fn) in git_files]
...
# an existing dir escapes its metacharacters so dir names are never globs
if fname.exists():
    if fname.is_file():
        all_matched_files.add(str(fname)); continue
    word = re.sub(r"([\*\?\[\]])", r"[\1]", word)
...
elif abs_file_path in self.coder.abs_read_only_fnames:
    can_edit = (self.coder.repo.path_in_repo(matched_file)
                if self.coder.repo
                else abs_file_path.startswith(self.coder.root))
    if can_edit:
        self.coder.abs_read_only_fnames.remove(abs_file_path)
        self.coder.abs_fnames.add(abs_file_path)
```

**Flow (word stage):** aiderignore/`--subtree-only` skip (:811) → literal existing file collected → existing DIRECTORY has glob metachars escaped before pattern use (:820) → `glob_filtered_to_repo` expands and tracked-filters → wildcard-with-no-match refuses creation → repo-less dir errors with a `/git add` hint → unmatched plain word offers consented `touch()` (parents mkdir; OSError caught).
**Flow (file stage, sorted candidates):** outside-root refusal when auto_commits and not an image (:849-857) → `.gitignore` refusal unless `--add-gitignore-files` → already-editable notice → **read-only→editable promotion gated on `path_in_repo`** (out-of-root read-only files can never promote) → image vision-capability check against `main_model.info["supports_vision"]` → `io.read_text` None guard before insertion + `check_added_files()`.
**Invariant:** glob expansion must be intersected with the tracked set BEFORE anything enters state; promotion to writable requires proof the path is inside the repo.
**Probe:** direct tests: `tests/basic/test_commands.py::test_cmd_add_with_glob_patterns` (:159) pins that `*.py` adds only tracked .py files and skips test.txt; `test_cmd_add_no_match_but_make_it` (:199) pins consented creation of `[abc].nonexistent`. Executed this pass via `.venv/bin/python -m pytest tests/basic/test_commands.py -k 'test_cmd_add ...' -q` → **26 passed**.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "glob_filtered_to_repo", limit: 10 });
// rank-1: aider.aider.commands.Commands.glob_filtered_to_repo aider/commands.py 765-797
```

## Verdict
Adopt the two-stage admission with tracked-only glob filtering and repo-proof-gated read-only promotion. Adapt the specific refusal messages and the image/vision gate to your model metadata. Omit aider's `auto_commits` coupling in the outside-root check unless you port auto-commit semantics too. Direct tests cover glob filtering, subdir adds, outside-root, gitignored, and unicode cases; the promotion branch itself is exercised via `test_cmd_add_read_only_file`.
