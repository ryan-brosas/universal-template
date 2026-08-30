<!-- capsule-v2 -->
# Commit attribution matrix — who gets blamed for an AI edit, without lying about either party

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How does a harness label AI-authored commits (author/committer/co-author) so an explicit user flag always beats the default and a failed commit never leaks the swapped identity?

## Explicit-over-implicit attribution resolved inside commit(), applied by temporary env vars
**Path/Symbol:** `aider/repo.py`: `GitRepo.commit(...)` (:131-318), `set_git_env(var_name, value, original_value)` (:40-49).
**Signature:** `commit(fnames=None, context=None, message=None, aider_edits=False, coder=None) -> tuple[str, str] | None`.
**Data Shape:** five attribution knobs (`attribute_author`, `attribute_committer`, `attribute_commit_message_author`, `attribute_commit_message_committer`, `attribute_co_authored_by`) read from `coder.args` when a coder is attached, else GitRepo init values; each may be None (= implicit default True).

### Decisive source
```python
effective_author = True if attribute_author is None else attribute_author
effective_committer = True if attribute_committer is None else attribute_committer
prefix_commit_message = aider_edits and (
    attribute_commit_message_author or attribute_commit_message_committer
)
# co-authored-by takes precedence over renaming UNLESS the flag was explicitly set:
use_attribute_author = (
    aider_edits and effective_author and (not attribute_co_authored_by or author_explicit)
)
use_attribute_committer = effective_committer and (
    not (aider_edits and attribute_co_authored_by) or committer_explicit
)
...
with contextlib.ExitStack() as stack:
    if use_attribute_committer:
        stack.enter_context(set_git_env("GIT_COMMITTER_NAME", committer_name, original_committer_name_env))
    if use_attribute_author:
        stack.enter_context(set_git_env("GIT_AUTHOR_NAME", committer_name, original_author_name_env))
    self.repo.git.commit(cmd)
```

**Flow:** settings sourced from coder.args > GitRepo attrs -> explicit-vs-default resolution -> trailer `\n\nCo-authored-by: aider (<model>) <aider@aider.chat>` only for aider edits with the flag on -> paths staged individually (`git add -- <abs paths>`) or `-a` -> commit executed inside ExitStack-swapped `GIT_{COMMITTER,AUTHOR}_NAME` = "<user.name> (aider)" -> hash+message returned; ANY_GIT_ERROR prints "Unable to commit" and returns None.
**Invariant:** env originals are restored even when the commit fails (set_git_env's finally restores or deletes); author-name modification NEVER applies to user commits (`aider_edits=False`); committer modification does; an explicit False always defeats co-authored-by precedence; the "aider: " message prefix requires BOTH aider_edits and a commit-message attribution flag.
**Probe:** `tests/basic/test_repo.py` — `test_commit_with_custom_committer_name` (:192), `test_commit_with_co_authored_by` (:267), `test_commit_co_authored_by_with_explicit_name_modification` (:318), `test_commit_ai_edits_no_coauthor_explicit_false` (:375). Executed GREEN this run via repo `.venv` (suite: 30 passed, 1 skipped). Anchors: `grep -nF 'use_attribute_author = (' aider/repo.py` -> :258; `grep -nF 'GIT_COMMITTER_NAME' aider/repo.py | head -3` -> :292/:302.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "set_git_env", limit: 3 });
// resolves aider/repo.py set_git_env Function :40-49 rank-1
```

## Verdict
Adopt the truth table (explicit beats implicit; co-author beats renaming unless explicit; author rename gated on AI edits) and the restore-on-failure env swap as the attribution contract. Adapt identity strings, trailer wording, and flag plumbing to the host. Omit Aider's argparse wiring; do not port the behavior as git hooks — it depends on running inside the committing process.
