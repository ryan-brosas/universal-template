# PR body format and push rules

The PR body follows the repository's own template first
(`.github/pull_request_template.md`); this reference defines the evidence
category each section must carry. Current template sections:

1. Summary: what changed, stated as the user-visible result
2. Why: the problem this solves; issue linkage lives here (`Closes #N` only
   when the PR fully fixes the issue, `Refs #N` when informational, never a
   guessed closure)
3. Verification: only checks actually run, with results (commands, exit
   codes, run links). `git diff --check` on the branch range.
4. Risks: regression / compatibility / migration / performance / security, or
   None identified
5. Reference / Prior Art: repo, path, revision, ADOPT/ADAPT/INSPIRATION; else N/A
6. Visual Evidence: rendered or runtime proof for visual changes; else N/A.
   Model review is not rendered proof.
7. Breaking Changes / Migration: what breaks and how to migrate; else N/A

## Rules

- Every claim traces to real evidence: a diff, a command with its exit status,
  or a run link. Absent values are `None` or N/A, never fabricated.
- Visual changes need actual before/after rendered evidence; text-only changes
  state N/A.
- Metadata (labels, reviewers, milestone) is set by repository automation or
  explicit user request, not hand-copied: area labels come from changed paths,
  type and breaking-change labels come from the PR title via
  `scripts/pr-metadata.py`.
- CI state is watched (`gh pr checks` / `gh run watch`) and recorded as
  observed. A failing required check blocks the merge; it does not force the
  PR back to draft.
