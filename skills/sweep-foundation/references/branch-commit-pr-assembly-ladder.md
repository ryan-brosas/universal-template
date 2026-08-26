<!-- capsule-v2 -->
# Branch/commit/PR assembly ladder — how does a planned change-set become a named branch, commit, and PR without collisions?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** How do you name and create a working branch under contention, and in what order must commit, sanitize, PR-create, and draft-conversion happen?

## Collision-retry branch naming + ordered commit→sanitize→PR pipeline
**Path/Symbol:** `sweepai/utils/github_utils.py:389-431` (`create_branch`); `sweepai/handlers/on_ticket.py:547-716` (step-3 assembly) (line range).
**Signature:** `def create_branch(repo: Repository, branch: str, base_branch: str = None, retry=True) -> str`.
**Data Shape:** Branch name from title via `"sweep/" + to_branch_name(title)`; `modify_files_dict: dict[path, {contents, ...}]`; returns final branch name string.

### Decisive source
```python
try:
    test = repo.get_branch("sweep")
    assert test is not None
    # If it does exist, fix
    branch = branch.replace("/", "_")  # Replace sweep/ with sweep_ (temp fix)
except Exception:
    pass

repo.create_git_ref(f"refs/heads/{branch}", base_branch.commit.sha)
return branch
...
for i in range(1, 10):
    try:
        _hash = get_hash()[:5]
        repo.create_git_ref(f"refs/heads/{branch}_{_hash}", base_branch.commit.sha)
        return f"{branch}_{_hash}"
    except GithubException:
        pass
```
```python
commit_message = pull_request_bot.get_commit_message(...)[:50]
new_file_contents_to_commit, files_removed = validate_and_sanitize_multi_file_changes(...)
...
pr: GithubPullRequest = repo.create_pull(..., draft=False)
...
convert_pr_draft_field(pr, is_draft=False, installation_id=installation_id)
```

**Flow:** clean name → if a branch literally named `sweep` exists, swap `/`→`_` → create ref at base sha; on GithubException retry up to 9 times with `_hash[:5]` suffixes; exhausted retries raise. In `on_ticket`: plan FCRs → create branch → apply file-change requests → truncate LLM commit message to 50 chars → sanitize multi-file contents (drops polluted paths; emits posthog `polluted_commits_error`) → commit → non-draft PR → best-effort assignee ("probably a bot") → revert-button comment only when >1 file changed → label + rocket reaction → watch failing actions / email / **draft conversion last** (`convert_pr_draft_field(pr, is_draft=False)`).
**Invariant:** The returned branch name is authoritative — callers must use the function's return value because retries rename the branch. Sanitization runs AFTER planning but BEFORE committing so polluted paths never reach git. PR creation precedes cosmetic steps so a failure in decoration leaves a usable PR behind.
**Probe:** No direct unit test for `create_branch` (coverage caveat). Deterministic probe = read the retry loop bound (exactly 9 attempts) and confirm `_hash[:5]`; graph retrieve executed at pin shows `create_branch` with 2 callers / 4 callees.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", file_pattern: "sweepai/utils/github_utils.py", name_pattern: "create_branch|refresh_token|sanitize_string_for_github", limit: 10 });
// executed at pin: create_branch github_utils.py 389-431, refresh_token :1102-1105,
// sanitize_string_for_github :1068-1098
```

## Verdict
Adopt collision-retry naming with hash suffixes and always-use-returned-name semantics; adopt the ordering commit→sanitize→PR→decorate→convert-draft as a durability ladder; adapt the 50-char truncation and button rendering to your UI conventions; omit Sweep's temp-fix `/`→`_` special case once your namespace guarantees no bare `sweep` branch.
