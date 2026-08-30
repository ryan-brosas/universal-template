# Templates & essentials inventory

Installed globally at:

- `~/.agents/templates/` - the CLI-neutral format templates
- `~/.agents/essentials/` - the operating baseline docs

Source: the pi-template repo (`~/.agents (absorbed from the retired pi-template repo)`); re-absorb
from it on demand to keep these current.

## Format templates

`adr.md` `agents.md` `design.md` `foundation-skill.md` `foundation-capsule.md`
`github-pr-ci.yml` `issue.md` `prd.md` `project-context.md` `proposal.md` `pull-request.md` `readme.md` `roadmap.md` `skill.md` `tasks.md`

Retired in the entry-architecture refactor (recoverable from Git history):
`project.md`, `tech-stack.md`, `state.md`, `user.md` — persistent project
artifacts are now selective (`project-bootstrap` Mode B / `goal-setup`), not a
default pack.

Usage mapping (what each rendered file's template drives):

| Template | Rendered into | Owner |
| --- | --- | --- |
| `agents.md` | project `AGENTS.md` | `project-bootstrap` (Mode B/C) |
| `project-context.md` | `docs/project-context.md` (or repo-native location) | `project-bootstrap` (Mode B, optional) |
| `roadmap.md` | roadmap doc | explicit user request only |
| `foundation-skill.md` / `foundation-capsule.md` | new skill/capsule leaves | `leverage-capture` |
| `skill.md` | the SKILL.md skeleton | `writing-skills`, `leverage-capture` |
| `github-pr-ci.yml` | the project GitHub Actions quality workflow | `github-actions-engineering`, `push-pr` |
| `pull-request.md` | the PR body template | `push-pr`, project PRs |
| `readme.md` | the repository README | `project-bootstrap` (new repos) |

## The essentials (operating baseline)

File name = core principle:

1. `objectives.md` - purpose before process
2. `operating-philosophy.md` - the overall baseline
3. `stack-your-leverage.md` - mechanical checks before rules
4. `guiding-small-model.md` - write for small models too
5. `enforce-code-quality-mechanically.md` - inference + prevent
6. `how-to-build-good-tests.md` - what "good" means
7. `README.md` - index & how they fit

When proposing a new rule, first check whether the right fix is a mechanical
check, not just a behavioral prompt.
