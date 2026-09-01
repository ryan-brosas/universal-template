---
name: project-bootstrap
description: "Use when entering a new or unfamiliar repository, initializing a greenfield project workspace, or intentionally establishing lightweight persistent project-level agent context."
---

# Project Bootstrap

## When to Use / NOT

- **Use when:** entering a new or unfamiliar repository, greenfield project
  setup, or intentional lightweight project governance.
- **NOT when:** continuing ordinary work in a known repo; that stays in the
  normal development loop.

## Core Principle

Initialization teaches the agent how to enter the project, it does not document the universe. Default to read-only understanding; create persistent artifacts only when durable, non-obvious context earns them; reconcile rather than rebuild on later runs.

## Workflow: Pick a mode from repository state + user intent

| Situation | Mode |
|---|---|
| "help me understand / set me up on this repo", unfamiliar checkout | **A, Onboarding** (read-only, default) |
| "set up this repo for long-term agent work", "create project instructions" | **B, Govern** |
| empty/minimal directory, "start a new project" | **C, Greenfield** |
| later invocation on a bootstrapped repo | **D, Refresh** (reconcile) |

## Mode A, Onboarding (read-only)

Inspect enough to answer: *What is this? How do I run it? How do I test it? Where are the main seams? What should I know before touching it?*

Read, as relevant: repo root, local `AGENTS.md`/instructions, README, manifests, lockfiles, language/runtime files, project structure, main entrypoints, real build/test/lint commands (run them, a command you have not run is not verified), existing CI, current dirty state, docs, obvious generated/vendor directories. Route deeper questions through `evidence-router`, direct source for small repos, Fovea for large active codebases, Steroid for exact semantics, Codebase Memory only when cross-repo discovery closes a gap. Recent Git history only when useful.

**Project-local prior art (cheap inventory):** when `reference/` or
`reference/web/` exists at the repo root, list top-level entry names only
(filesystem listing; no bulk read): `reference/<name>/` checkouts and
`reference/web/<site>/` captures. Note what reusable assets exist so later
work can consult them; do not ingest every reference during onboarding.

**Output, a compact session summary (conversation, not files):**

```
Project / Type / Stack / Package+runtime
Run / Test / Build (verified commands)
Key paths · Important boundaries · Current state · Known traps
Reference assets · (when present: names under reference/ and reference/web/)
```

No persistent files. No roadmap, user profile, project encyclopedia, tech-stack cache, or architecture summary. The user asked to enter the project, not document it.

## Mode B, Govern

Inspect what already exists first (AGENTS.md, instructions, docs). Create only what is missing and valuable:

- `AGENTS.md` from `templates/agents.md`, local Verify commands (run them), repository facts, non-obvious invariants, traps, enforced conventions only.
- Optionally ONE compact context file (`docs/project-context.md` from `templates/project-context.md`, or the repository's native location), 30–60 lines of expensive-to-reconstruct intent: decisions, constraints, boundaries, traps, intentionally unsupported behavior. Not a manifest cache.

GitHub setup → delegate to `github-repo-setup`. CI → `github-actions-engineering`. Do not run either automatically.

## Mode C, Greenfield

Do not run existing-repo deep detection on an empty directory. First ask: is the direction clear?

- **Unclear** → `brainstorming` first (ground in the user's problem, not fabricated architecture).
- **Clear** → scaffold the project (native tooling of the chosen stack), then: GitHub requested? → `github-repo-setup`. CI requested? → `github-actions-engineering`. Neither happens automatically, report that CI/repo setup is absent and let the user decide.
- **Baseline requested**, phrases like "our standard setup", "our baseline", "production-ready", "OSS-ready", "full setup" authorize the standard baseline after scaffolding: `github-repo-setup` at the maturity class from its `references/setup-matrix.md`, then `github-actions-engineering`, then `git-workflow-and-versioning` only when the project is versioned. "Start a new project" or "scratch project" requests none of it, scaffold, report what was skipped.
- Complex/high-risk project creation itself → `goal-setup` before scaffolding.

## Mode D, Refresh (reconcile, never rebuild)

Inspect → compare → update only what is stale. Preserve hand-written decisions and intentional local instructions, regenerate nothing from scratch. Detect stale guidance (retired tool names, dead commands, outdated invariants) and fix exactly that. A second run on a current repository reports "nothing to change".

## Red Flags

- Creating default host artifact packs by default (for pi: `.pi/project.md`,
  `.pi/state.md`, and similar). HARD-GATE. Host runtime state belongs under
  the host config (e.g. `~/.pi/` for pi) or explicit project governance, not
  automatic bootstrap output.
- Creating a user-profile/personal-preference file in a repository. HARD-GATE.
- Persisting machine-recoverable facts (versions, commands, branch, dirty state, dependency lists), detect them when needed instead.
- Running GitHub or CI setup as an automatic side effect of local bootstrap.
- Overwriting intentional local instructions during refresh.
- Writing a failing command as the project's verify command.

## Verification

Mode A: every command in the summary was executed (exit code cited). Each written file in Modes B/C exists, reconciles against prior content, and holds only verified or `[NEEDS CLARIFICATION]` claims. In Mode D the diff shows only the stale-set that changed.

## References

- `~/.agents/templates/agents.md`, project AGENTS source
- `~/.agents/templates/project-context.md`, compact durable-context source
- `~/.agents/templates/roadmap.md`, only when the user explicitly requests a roadmap
- `../github-repo-setup/SKILL.md`, repository governance (delegated)
- `../github-actions-engineering/SKILL.md`, CI/workflows (delegated)
- `../brainstorming/SKILL.md`, unclear direction (delegated)
- `../goal-setup/SKILL.md`, durable execution contract (delegated)
