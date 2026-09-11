<!-- capsule-v2 -->
# Repo sanity gate — index-version detection and UnicodeDecodeError triage before first use

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** Before trusting a git repo for automated commits, which failure modes must a tool distinguish — and how does it tell the user exactly how to fix each?

## get_tracked_files() as probe: clean → OK; version-in-(1,2) string → update-index hint; AssertionError → same; UnicodeDecodeError → filesystem-encoding explainer
**Path/Symbol:** `aider/main.py`: `sanity_check_repo(repo, io)` (:412-448); gated by `--skip-sanity-check-repo` (:924/:929); `ANY_GIT_ERROR` tuple imported from aider.repo (:35).
**Signature:** returns True (no repo / healthy repo) or False (fatal); populates error_msg from the FIRST failing branch.
**Data Shape:** bad_ver detection is substring matching: `"version in (1, 2)" in error_msg` for GitCommandError paths, unconditional True for AssertionError (gitpython raises it on ancient index formats).

### Decisive source
```python
try:
    repo.get_tracked_files()
    if not repo.git_repo_error:
        return True
    error_msg = str(repo.git_repo_error)
except UnicodeDecodeError as exc:
    error_msg = (
        "Failed to read the Git repository. This issue is likely caused by a path encoded "
        f'in a format different from the expected encoding "{sys.getfilesystemencoding()}".\n'
        f"Internal error: {str(exc)}"
    )
except ANY_GIT_ERROR as exc:
    ...
    bad_ver = "version in (1, 2)" in error_msg
except AssertionError as exc:
    ...
    bad_ver = True
if bad_ver:
    io.tool_error("Aider only works with git repos with version number 1 or 2.")
    io.tool_output("You may be able to convert your repo: git update-index --index-version=2")
```

**Flow:** GitRepo construction (:903-922, FileNotFoundError silently means "no git") → unless skipped, sanity_check probes tracked-file enumeration → branches produce tailored remediation: index-version conversion command + docs URL offer (`io.offer_url(urls.git_index_version, ...)`), encoding explainer naming sys.getfilesystemencoding(), or generic corrupt-repo message.
**Invariant:** the gate runs BEFORE any commit-capable session starts and after repo creation so brand-new repos pass trivially; skip flag exists for power users but analytics still records "Repository sanity check failed" exits.
**Probe:** direct tests executed GREEN this run via repo venv (`python -m pytest tests/basic/test_sanity_check_repo.py -q`: **5 passed**). Deterministic anchors: `grep -nF 'version in (1, 2)' aider/main.py` → :434; `grep -nF 'get_tracked_files()' aider/main.py | head -1` → :422.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "sanity_check_repo", limit: 3 });
// resolves main.py sanity gate line-exact
```

## Verdict
Adopt the probe-and-triage shape before enabling any agent-driven git writes; keep the three-way error taxonomy (index format / path encoding / corrupt). Porters who catch bare Exception here erase the remediation hints that make the tool usable on legacy repos.
