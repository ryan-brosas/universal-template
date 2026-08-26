<!-- capsule-v2 -->
# file-selector-toml-context — How is the improve-mode context chosen, persisted, and kept small?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** What is the editor-in-the-loop TOML selection protocol and its filter rules?

## Context selection seam
**Path/Symbol:** `gpt_engineer/applications/cli/file_selector.py:FileSelector` (IGNORE_FOLDERS :53, FILE_LIST_NAME :54, ask_for_files :79-121, editor_file_selector :123-210, get_current_files :379-416); persistence at `<project>/.gpteng/file_selection.toml`.
**Signature:** `ask_for_files(skip_file_selection=False) -> tuple[FilesDict, bool]` (files, is_linting).
**Data Shape:** TOML `[files] "<rel/path>" = "selected"` where UNCOMMENTED entries are selected; `[linting] "linting" = "off"` disables black-format linting pass.

### Decisive source
```python
IGNORE_FOLDERS = {"site-packages", "node_modules", "venv", "__pycache__"}
...
# get_current_files filters:
if any(part.startswith(".") for part in parts): continue     # hidden
if any(part in self.IGNORE_FOLDERS for part in parts): continue
if relpath.name == "prompt": continue                          # never upload the prompt itself
...
if is_git_repo(project_path) and "projects" not in project_path.parts:
    all_files = filter_by_gitignore(project_path, all_files)   # git check-ignore --no-index --stdin
```

**Flow:** test/skip mode reads TOML directly (asserts presence) → else generate full filtered tree → render every line commented (`# path = "selected"`) → open $EDITOR (EDITOR env, fallback ladder gedit/notepad/nvim/write/nano/vim/emacs) → user uncomments selections → parse back, merge NEW files as commented (merge_file_lists), re-write → collect contents with FileNotFoundError/UnicodeDecodeError warnings skipped.
**Invariant:** (1) DEFAULT-DENY on first run: everything commented until user opts in — context minimization by construction. (2) The literal filename "prompt" is excluded from selection — prevents recursive prompt-upload. (3) gitignore filtering applies ONLY inside git repos AND outside any "projects" path segment (protects gpt-engineer's own bundled examples). (4) GPTE_TEST_MODE env var switches to TOML-driven headless operation — the automation seam. (5) is_linting rides OUT-OF-BAND (second tuple element + mutable class attr) because linting happens AFTER selection on the selected FilesDict.
**Probe:** `grep -n '"prompt"' gpt_engineer/applications/cli/file_selector.py` → :408 exclusion site.
**Probe:** `grep -n 'GPTE_TEST_MODE' gpt_engineer/applications/cli/file_selector.py` → :92 headless switch.
**Probe:** `tests/core/test_file_selector_enhancements.py` pins merge/filter behaviors.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "FileSelector ask_for_files IGNORE_FOLDERS file_selection.toml", limit: 10 });
```

## Verdict
Adopt default-deny TOML selection + ignore-folder taxonomy + prompt-name exclusion for any context-gathering agent; adapt editor UX to non-interactive pickers; keep the gitignore delegation (check-ignore --no-index works without a commit).
