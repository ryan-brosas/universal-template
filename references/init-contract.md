# Init contract — the pi-template /init workflow, ported to the global skill

Source of truth: `AGENTS.md` + the init workflow distilled in
`skills/workflow-lifecycle/references/init.md` (the retired global `prompts/`
files were folded into that skill).
This capsule is the CLI-neutral distillation that the `pi-template` skill enforces anywhere.

## When to apply

Any workspace bootstrap or re-govern: greenfield repo, brownfield codebase, or a workspace that
needs context artifacts (AGENTS.md, .pi/*). Run once per project; flags narrow the run:

| Flag | Scope |
| --- | --- |
| (none) | full deep init — AGENTS.md, project, tech-stack, roadmap, state, user |
| `--context` | roadmap.md + state.md only (planning context rerun) |
| `--user` | user.md only |

## Phase order (read-only until approval)

1. **Deep detect.** Package manager + deps with versions, build/test/lint/dev commands, CI job
   list, existing AI rules (`.cursorrules`, `.github/copilot-instructions.md`), top-level layout,
   git history (last ~50 commits), source structure, entrypoints (CLI/server/workers/jobs),
   import graph, data stores/schemas/migrations, external integrations, deployment/runtime config,
   testing layout, security boundaries, generated files (.gitignore).

   Confirm every command the artifact will cite actually runs; a command that fails
   must not be written as the completion command.

2. **Preview.** Detection table → confirm (Yes / Adjust / Cancel). Write nothing before approval.

3. **Render artifacts.** Templates come from `~/.agents/templates/` (installed globally):
   `agents.md`, `project.md`, `tech-stack.md`, `roadmap.md`, `state.md`, `user.md`.

## Artifact idempotency matrix (exact)

| File | Rule |
| --- | --- |
| `AGENTS.md` | improve in place, never overwrite blindly; leads with the canonical completion command; points to `.pi/project.md` |
| `.pi/project.md` | create if missing; ask before overwrite (architecture/product context) |
| `.pi/tech-stack.md` | overwrite with detected values (auto-regenerated) |
| `.pi/roadmap.md` / `.pi/state.md` | skip if exists; ask before overwrite |
| `.pi/user.md` | skip if exists; ask before overwrite |

## Evidence & quality contract

- Minimum content per artifact: every template section covered; blanks are `[NEEDS CLARIFICATION: reason]`, never silently dropped.
- Every claim/command/restriction traces to file:line, config, command output, or user answer; a claim without a citation is a draft.
- Cross-file consistency: commands, counts, paths, architecture terms agree across prompt/templates/artifacts.
- Preview material changes; no invented facts (versions, commands, integrations, preferences).
- After writing, run every recorded command + gates and report per-artifact results.
- Merge verified user-authored constraints; remove stale generated guidance only with approval.
- Keep detailed architecture in `.pi/project.md`; AGENTS.md gets a compact product map + pointer.

## GitHub phase (optional, /init only)

Read-only detection before any proposal: `git remote get-url origin`, `gh repo view`;
mutations (`gh repo create`, push, GitHub Project enrollment) each need separate
approval; no auto-create, owner never guessed, private by default.

## Output

Report per artifact: created / updated / skipped / clarified / verified, the evidence commands
run, cross-file consistency check, GitHub setup state, next command recommendation.