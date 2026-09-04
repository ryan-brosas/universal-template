<!-- capsule-v2 -->
# Git CLI-wrapper tool hardening — how do you expose CLI-wrapping git tools to an LLM so flag injection, path traversal, and out-of-scope repositories are structurally impossible?

**Source:** modelcontextprotocol/servers MIT `main@599dafc1054550a6eeb87a6545c1e1b03b3ca827`; Codebase Memory `servers` (root `/mnt/hdd/utopia/inspo/servers`; the pass-9-era path-slugged project name no longer resolves after the disk re-org — same index re-registered under the short name). **Question:** what is the complete defense ladder a git MCP server needs between an untrusted LLM argument and a shell-adjacent CLI?

## Four-layer defense ladder over GitPython (prefix-reject -> ref-validate -> `--` separator -> resolve+relative_to scoping)
**Path/Symbol:** `src/git/src/mcp_server_git/server.py` — `git_diff` :120–126; `git_add` :132–153; `git_log` timestamp guard :159–171; `git_create_branch` :200–212; `git_checkout` :214–221; `git_show` :225–250; `validate_repo_path` :252–270; `git_branch` contains/not_contains guard :273–305; `call_tool` scoping call site :487–495; startup fail-closed in `serve` :311–317.
**Signature:** module-level pure functions `def git_<op>(repo: git.Repo, ...) -> str | list[str]` plus `def validate_repo_path(repo_path: Path, allowed_repository: Path | None) -> None` — guards raise `BadName` (GitPython unknown-ref) or `ValueError`, asserted by direct tests via `pytest.raises`; `call_tool` applies scoping BEFORE any repo object is built (:491–495).
**Data Shape:** every tool input carries `repo_path: str`; stringly-typed refs/timestamps/paths are the attack surface. `context_lines: int = 3` rides into `--unified=N`. Read-only tools annotate `{readOnlyHint: True, destructiveHint: False, idempotentHint: True, openWorldHint: False}`; RESET flips destructiveHint=True; COMMIT/CHECKOUT/CREATE_BRANCH flip idempotentHint=False (:321–456).

### Decisive source
```python
// src/git/src/mcp_server_git/server.py:132-153 (verbatim)
def git_add(repo: git.Repo, files: list[str]) -> str:
    if files == ["."]:
        repo.git.add(".")
    else:
        # Defense in depth: validate each path resolves within the repository
        # working tree to prevent path traversal (e.g. '../../etc/passwd' or an
        # absolute path) from staging files outside repository boundaries.
        repo_root = Path(repo.working_dir).resolve()
        for f in files:
            try:
                resolved = (repo_root / f).resolve()
            except (OSError, RuntimeError):
                raise ValueError(f"Invalid path: '{f}'")
            try:
                resolved.relative_to(repo_root)
            except ValueError:
                raise ValueError(
                    f"Path '{f}' is outside the repository '{repo_root}'"
                )
        # Use '--' to prevent files starting with '-' from being interpreted as options
        repo.git.add("--", *files)
    return "Files staged successfully"

// :252-270 (verbatim) — server-start repository scoping, applied to EVERY call_tool
def validate_repo_path(repo_path: Path, allowed_repository: Path | None) -> None:
    if allowed_repository is None:
        return  # No restriction configured
    try:
        resolved_repo = repo_path.resolve()
        resolved_allowed = allowed_repository.resolve()
    except (OSError, RuntimeError):
        raise ValueError(f"Invalid path: {repo_path}")
    try:
        resolved_repo.relative_to(resolved_allowed)
    except ValueError:
        raise ValueError(
            f"Repository path '{repo_path}' is outside the allowed repository '{allowed_repository}'"
        )
```

**Flow:** `serve(repository)` validates the optional repo arg at startup and RETURNS WITHOUT RUNNING if it is not a git repo (:311–317, fail-closed boot) → per call: `validate_repo_path(arguments["repo_path"], repository)` → `git.Repo(repo_path)` → per-tool guard chain → GitPython OBJECT api where possible (`repo.rev_parse`, `repo.index.commit`, `repo.iter_commits`, `repo.commit`) and `repo.git.*` passthrough only where the object API lacks coverage (`status/diff/add/branch/checkout`). Ref-taking tools (`git_diff`, `git_checkout`, `git_show`, `git_create_branch`) all do prefix-reject then ref-existence validation BEFORE the passthrough; `git_diff` composes both with `--unified={n}`.
**Invariant:** FOUR load-bearing layers, each covering what the previous cannot: (1) **prefix-reject `-`** kills flag injection even when the ref EXISTS — the threat model is filesystem manipulation writing `.git/refs/heads/--output=evil.txt` (an mcp-filesystem-style companion server), not just typos; (2) **ref-existence validation via `repo.rev_parse` before the CLI call** converts unknown targets into typed errors and guarantees the passthrough argument is a real rev; (3) **`--` end-of-options separator** for file lists (the only defense that works for paths that LEGITIMATELY start with `-`); (4) **resolve()+relative_to containment** twice — staged file paths against `repo.working_dir` (CVE-2026-27735 path-traversal fix), and the requested `repo_path` against the `--repository` launch arg, symlink-aware on BOTH sides because both are resolved first. Scoping is opt-out: `allowed_repository=None` means unrestricted multi-repo mode. Caveat: `list_repos` (:458–485, roots-based discovery) is defined but never invoked by `call_tool` — dead code from an earlier auto-discovery design; do not copy it as load-bearing.
**Probe:** `src/git/tests/test_server.py` (510L) pins every layer: `test_git_add_rejects_path_traversal` :112–125 (comment cites CVE-2026-27735; accepts rejection from EITHER layer — asserts the property, not the layer), `test_git_add_rejects_absolute_path_outside` :127–136, six `test_validate_repo_path_*` :283–341 incl. `symlink_escape`, `test_git_diff_rejects_flag_injection` :344–353, `test_git_diff_rejects_malicious_refs` :412–435 (writes the malicious ref into .git/refs and asserts rejection + no output file), twins for checkout/show/create_branch/log/branch :356–510. Live-run 2026-08-25: **43 passed** (venv: gitpython 3.1.59, pytest 9.1.1, mcp>=1.29).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "mcp_server_git server git_status git_diff tools repository" });
await mcp.codebase_memory.get_code_snippet({ project: "servers", qualified_name: "servers.src.git.src.mcp_server_git.server.validate_repo_path" });
```
(Live-executed at `599dafc1`: BM25 returns 174 hits led by git_status/git_diff/git_diff_unstaged/staged; get_code_snippet resolves validate_repo_path :252–270 and git_add :132–153 byte-identical to disk.)

## Verdict
Adopt the four-layer ladder wholesale for ANY tool that forwards LLM strings toward a CLI or parser with option syntax: reject leading `-` by value, validate existence through the domain API (not the CLI) before dispatch, force `--` before positional file lists, and scope every request path with resolve+relative_to against BOTH the working tree and a launch-time root. Prefer the object API over passthrough wherever it exists — objects cannot receive flags. Keep annotations honest (RESET really is destructive; commit/checkout/create_branch really are non-idempotent). Map guard failures to tool-execution errors, not protocol errors, so the model can retry with corrected arguments. Direct-test coverage complete at `599dafc1`.
