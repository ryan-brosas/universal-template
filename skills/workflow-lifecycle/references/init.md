# init - workspace bootstrap contract

Applies to workflow-lifecycle command init. Source prompt: ~/.agents/prompts/init.md.

## When to apply
First-time project bootstrap or a re-govern pass, once per project.

## Flags
| Flag | Scope |
|---|---|
| (none) / --all | full deep init |
| --deep | explicit full discovery (already default) |
| --context | roadmap + state only |
| --user | user.md only |

## Phase 1 - Detect (read-only)
Run through the context layer first (search_graph on the covered project, trace_path on composition roots, then read 3-5 representative files to ground it). Then confirm:
- package manager + dependency versions (manifest + tool existence)
- build/test/lint/dev commands - validate each actually runs; a failing command is never written
- CI/CD job list from workflow files
- existing AI rules (.cursor/rules, .github/copilot-instructions.md)
- top-level layout, git history tail (~50 commits), source structure
- entrypoints (CLI/server/workers/jobs), import direction, data stores, migrations
- external integrations, deployment/runtime config, env/health/rollback
- testing layout + gaps, security boundaries, generated files + untracked state

## Phase 2 - Preview
Render the detection table and ask Yes / Adjust / Cancel. Nothing is written before approval.

## Phases 3-7 - Artifacts (idempotency matrix)

| File | Rule |
|---|---|
| AGENTS.md | improve in place, never overwrite blindly; leads with the canonical completion command; pointer to .pi/project.md |
| .pi/project.md | create if missing; ask before overwrite (architecture/product context) |
| .pi/tech-stack.md | overwrite with detected values; separate project deps from host tools |
| .pi/roadmap.md / .pi/state.md | skip if exists; keep before overwrite |
| .pi/user.md | skip if exists; keep before overwrite |

Templates come from ~/.agents/templates/ (agents.md, project.md, tech-stack.md, roadmap.md, state.md, user.md).

## Artifact quality contract
1. By-default minimum content per artifact; empty sections become `[NEEDS CLARIFICATION: reason]`, never dropped silently.
2. Every claim traces to evidence (file:line, config, output, user answer).
3. Cross-file consistency everywhere.
4. Preview material changes before writing.
5. No invented facts; unknown values are asked.
6. After writing, run the recorded commands + gates; report per-artifact results.
7. Deep architecture stays in .pi/project.md; AGENTS.md waits compact.

## Phase 8 - Persist
Files are the durable record; the session store keeps working context (memory.recall).

## Phase 9 - GitHub (optional)
Only when gh is present; read-only detection first (git remote get-url origin, gh repo view); creation and push are separate approvals; owner never guessed; private by default.

## Output
Per artifact state created / updated / skipped / clarified / verified, evidence commands run, cross-file consistency confirmation, GitHub setup state, recommended next command.