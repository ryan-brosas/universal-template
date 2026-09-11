<!-- capsule-v2 -->
# Git-repo bootstrap ladder — auto-init consent, identity backfill, and .gitignore self-protection

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** What must a coding agent do when launched outside any git repo — and what does it write into the user's repo on their behalf?

## Offer init (never in $HOME); backfill user.name/email with loud warnings; add .aider*/.env to .gitignore only with consent
**Path/Symbol:** `aider/main.py`: `setup_git(git_root, io)` (:101-152), `make_new_repo(git_root, io)` (:88), `check_gitignore(git_root, io, ask=True)` (:155-206); guards: home-dir refusal :117-121, `--no-git` directory rejection :709-711.
**Signature:** `git.Repo.init` wrapped in `except ANY_GIT_ERROR` (issue #1233: unreadable dir → tool_error + str(err), NO crash, returns None).
**Data Shape:** gitignore patterns added: `.aider*` always-if-not-ignored; `.env` ONLY if the file exists AND is not already ignored.

### Decisive source
```python
elif cwd == Path.home():
    io.tool_warning("You should probably run aider in your project's directory, not your home dir.")
    return
elif cwd and io.confirm_ask("No git repo found, create one to track aider's changes (recommended)?"):
    git_root = str(cwd.resolve())
    repo = make_new_repo(git_root, io)
...
if not repo.ignored(".aider"):
    patterns_to_add.append(".aider*")
env_path = Path(git_root) / ".env"
if env_path.exists() and not repo.ignored(".env"):
    patterns_to_add.append(".env")
...
with repo.config_writer() as git_config:
    if not user_name:
        git_config.set_value("user", "name", "Your Name")
        io.tool_warning('Update git name with: git config user.name "Your Name"')
```

**Flow:** after the true root settles → setup_git opens/creates the repo → reads user.name/user.email via `repo.git.config --get`, backfills "Your Name"/"you@example.com" placeholders WITH warnings telling how to fix → check_gitignore asks before appending patterns, preserves existing content (append with newline guard; read failures abort politely), and on write failure prints the exact patterns for manual addition.
**Invariant:** every mutation to the user's repository (init, config writes, .gitignore edits) sits behind either a confirm_ask or an explicit flag (`--gitignore` gates check_gitignore at :742-743) — the agent never silently rewrites ignore rules or identity; `.env` protection triggers only on existence so empty repos don't get boilerplate.
**Probe:** direct test `tests/basic/test_main.py::test_git_ignore**` family (executed green this run within the full basic suite run below). Deterministic anchors: `grep -cF 'patterns_to_add' aider/main.py` → **8**; `grep -nF 'not your home dir' aider/main.py` → :119.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "check_gitignore setup_git", limit: 3 });
// resolves setup_git/check_gitignore/make_new_repo in aider/main.py
```

## Verdict
Adopt the consent-gated bootstrap ladder verbatim for any agent that touches VCS state; adapt pattern names. Porters who skip the home-dir guard create stray repos in `$HOME`; porters who skip `repo.ignored()` checks append duplicate .gitignore lines on every launch.
