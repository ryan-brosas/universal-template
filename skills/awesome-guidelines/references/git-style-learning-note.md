# Git style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `git-style-*.md` capsules, `git-workflow-and-versioning`, `git-and-collaboration.md`.

## Sources read

| Source | What we extracted |
|---|---|
| [agis/git-style-guide](https://github.com/agis/git-style-guide) (CC BY 4.0) | Branch naming, logical commits, 50/72 message format, merge `--no-ff`, history rewrite rules, tags |
| [git/Documentation/SubmittingPatches](https://github.com/git/git/blob/master/Documentation/SubmittingPatches) | Imperative mood, problem/solution body structure, present-tense problem statement, commit references, patch-series rewrite ethics |
| [tbaggery commit messages](https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html) | Why subject/body split matters for `log`, `rebase -i`, `format-patch`, GitHub UI |
| [git/CodingGuidelines](https://github.com/git/git/blob/master/Documentation/CodingGuidelines) | Log messages as important as code; avoid style-only churn on unrelated work |
| Catalog | `git-and-collaboration.md`, `AGENTS.md` branch naming, repository-native title checks |

## Mental model

Git history is a **communication channel** to future readers (reviewers, bisect, release notes). Branches name *intent*; commits are *logical edits* with messages that explain **why**; merges/tags mark *releases*. Published history is **append-only** — rewriting shared branches destroys others' context. Local/unpushed history is clay: squash, fixup, reword until the series tells a clean story.

Two message traditions coexist in this catalog:

1. **Kernel/Git style** — imperative subject (~50 chars), blank line, wrapped body (~72) explaining problem → solution.
2. **Conventional commits** — `type(scope): description` enforced mechanically on branch ranges.

They compose: `feat(auth): migrate OAuth token storage` satisfies both if the body carries the kernel-style *why*.

## Decision tables

### Branch names

| Situation | Do |
|---|---|
| New feature | Short, lowercase, hyphens: `oauth-migration` |
| Ticket tracked | Prefix id: `issue-15`, `T321-new-feature` |
| Team parallel work | `feature-a/main`, `feature-a/alice` → merge up, then to main |
| After merge | Delete remote branch unless explicitly kept |

Catalog cap: ≤3 hyphen segments unless project AGENTS.md overrides.

### Commits (logical unit)

| Do | Don't |
|---|---|
| One logical change per commit | Mix unrelated fix + refactor + typo |
| Feature + its tests together | Split tests to a later commit |
| Order dependent commits so Y precedes X when X needs Y | Shuffle so bisect breaks |
| `git add -p` to stage hunks | One giant WIP commit before push |

Local-only WIP snapshots are allowed; **before push**, apply message and logical-split rules.

### Messages

| Field | Rule |
|---|---|
| Subject | Imperative, ~50 chars, capitalized (kernel) OR conventional prefix + description |
| Separator | Blank line before body (required for rebase/format-patch) |
| Body | ~72 wrap; present tense for problem; imperative for change; why > how |
| Footers | `Resolves: #n`, `Signed-off-by:` when project requires DCO |

### History rewrite

| Context | Rewrite OK? |
|---|---|
| Not pushed / only you | Yes — squash, fixup, rebase -i |
| Shared `main`, release, CI branches | **No** force-push |
| PR branch before merge | Team policy — often rebase/squash with consent |

### Merge

| Case | Preference |
|---|---|
| Multi-commit feature branch | `git merge --no-ff` preserves branch context (agis); many teams squash-merge — follow project |
| Linear history teams | Rebase onto target before merge |

## Edge cases

- **fixup/squash commits:** use `--fixup`/`--squash` + `--autosquash` so intent is machine-readable before rebase.
- **Dependency between commits:** cite SHA in message when referencing another commit (Git `SubmittingPatches` format: `abbrev (subject, date)`).
- **Conventional vs 50-char:** `feat(scope):` eats budget — keep description segment tight; put detail in body.
- **Style fix drive-by:** Git project says don't churn unrelated style; match local convention when touching a file.

## Anti-patterns

| Pattern | Why it hurts |
|---|---|
| `git commit -m "fix"` for non-trivial work | No body → rebase/log tools degrade; future you lacks *why* |
| Raw git log as changelog | Noise merges, WIP, typo commits — humans can't scan |
| Force-push `main` | Breaks clones, CI, other developers |
| `--no-verify` to skip hooks | Bypasses mechanical gates the project trusts |
| `git add .` in dirty worktree | Stages others' WIP (`git-workflow-and-versioning`) |

## Skill trace

- Capsules: `git-style-branches.md`, `git-style-commit-messages.md`, `git-style-history-and-merge.md`
- Application: `git-workflow-and-versioning/SKILL.md`
- Router: `coding-best-practices` → `git-and-collaboration.md`
