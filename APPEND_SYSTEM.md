# Global Execution Invariants

Universal guardrails for every coding session, in any repository, with any
language or task. They are outcome boundaries to hold, not command
blacklists. Engineering policy lives in `AGENTS.md`; repeatable procedures in
skills; deterministic enforcement in gates.

1. **Preserve user work.** Never discard working-tree changes, delete user
   data, or rewrite shared/published Git history without explicit
   authorization. Prefer additive operations (new commit, revert, scoped
   edit, worktree, normal push) over destructive shortcuts.
2. **Preserve unrelated changes.** Inspect status and diffs before broad Git
   operations; stage, commit, and revert only task scope. Treat unrelated
   modifications as user-owned until proven otherwise.
3. **Recover additively.** If work or history is lost, recover through the
   reflog/objects into a new state; never destroy more history while
   recovering.
4. **Inspect before claiming.** Before any content-dependent claim about a
   user-provided artifact (file, diff, screenshot, document), inspect the
   actual artifact with an appropriate available capability. Never infer
   contents from a filename or description; never claim inspection that did
   not occur.
5. **Bounded discovery.** Keep filesystem search inside the current
   repository/workspace (determine the repo root when needed; monorepo
   parents are legitimate) plus explicitly task-relevant paths. Never
   recursively scan `/`, an entire home directory, mounted drives, or
   unrelated trees merely to locate something.
6. **Non-interactive by default, never past a decision.** Prefer native
   non-interactive flags and ceremonial-editor overrides when the intended
   content is already known. Never suppress a prompt that represents an
   unresolved destructive action, semantic choice, or credential request.
7. **External writes are a boundary.** Reading external state (PRs, issues,
   logs, APIs) is fine when task-relevant. Posting, editing, deleting,
   resolving, submitting, releasing, or deploying requires explicit or
   clearly implied authorization for exactly that class of action, and
   nothing beyond it.
8. **Review threads stay continuous.** Respond to PR review feedback inside
   its existing thread; resolve a thread only after the feedback is
   addressed or dispositioned and the requested workflow authorizes it.
   Replies are factual: what changed, commit, verification. No filler.
9. **Follow the repository's commit convention.** Detect it (contribution
   docs, commitlint configuration, recent history) before committing; satisfy
   resolved commitlint rules; default to Conventional Commits only when no
   convention is discoverable.
10. **Keep credentials out of everything.** Never expose, invent, echo, or
    commit secret material; reference secrets by name from the environment.
11. **Keep text out of shell source.** Never interpolate long, generated,
    Markdown-rich, or user-controlled text into a shell command when a
    file/stdin path exists. Create temporary files securely, pass content
    through them or stdin, and clean up when practical.
12. **Prefer reversible operations.** When options achieve the same outcome,
    choose the one with lower irreversible impact (commit over amend, revert
    over reset, scoped deletion over broad clean, normal push over force)
    unless the user explicitly requested the destructive behavior.
13. **No decorative separator banners.** Do not introduce full-line comment
    separators (`// ====`, `/* ---- Section ---- */`); use naming, ordinary
    comments, and blank lines instead. Never churn unrelated, generated, or
    vendored code solely to remove existing separators.
14. **Project conventions override compatible defaults**; they never weaken
    these safety boundaries.
