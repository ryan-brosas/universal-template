<!-- capsule-v2 -->
# Commit messages — what makes a commit readable in `git log` and `rebase -i`?

**Source:** agis/git-style-guide; Git `SubmittingPatches`; tbaggery 2008; catalog `conventional-commit.py`. **Question:** What message shape survives tooling and still explains *why*?

## Subject/body seam
**Path/Symbol:** `.git/COMMIT_EDITMSG` on `git commit`.
**Signature:** line 1 = subject; line 2 = blank; line 3+ = body (~72 cols).
**Data Shape:** imperative mood; conventional commits optional prefix `type(scope):`.

### Decisive template
```text
feat(auth): migrate token storage to sealed cookie

Sessions previously stored tokens in localStorage, which exposed
them to XSS. Move to httpOnly sealed cookies and delete the legacy
read path. Resolves: #56
```

**Flow:** stage logical unit → `git commit` (editor, not `-m` for non-trivial) → subject ≤50 chars of *summary* → blank line → body: problem (present) → change (imperative) → footers.
**Invariant:** without blank line after subject, `rebase -i` and `format-patch` treat body as subject continuation (tbaggery).
**Probe:** `git log -1 --format=%B` shows blank line after first line; `CHECK_RANGE=... python3 scripts/conventional-commit.py` exit 0 when catalog applies.

## Logical commit seam
**Flow:** one logical change = one commit; feature + tests together; use `git add -p` to split hunks; `--fixup`/`--squash` for series cleanup before push.
**Invariant:** bisect requires each commit to be a coherent unit — split tests from feature breaks bisect.
**Probe:** `git show --stat` matches one stated intent; no unrelated paths without explanation.

## Verdict
Adopt kernel 50/72 + imperative + blank line; layer conventional prefix when catalog enforces it; omit `-m` one-liners for multi-file changes. learning note: `git-style-learning-note.md`.
