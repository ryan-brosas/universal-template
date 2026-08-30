# Templates & essentials inventory

Installed globally at:

- `~/.agents/templates/` - 18 CLI-neutral format templates
- `~/.agents/essentials/` - the operating baseline docs (8)

Source: the pi-template repo (`~/.agents (absorbed from the retired pi-template repo)`); re-absorb
from it on demand to keep these current.

## The 18 format templates

`adr.md` `agents.md` `design.md` `foundation-skill.md` `foundation-capsule.md`
`github-pr-ci.yml` `issue.md` `prd.md` `project.md` `proposal.md` `pull-request.md` `readme.md` `roadmap.md` `skill.md`
`state.md` `tasks.md` `tech-stack.md` `user.md`

Usage mapping (what each rendered file's template drives):

| Template | Rendered into | Owner |
| --- | --- | --- |
| `agents.md` | `AGENTS.md` | workflow-lifecycle init (full) |
| `project.md` | `.pi/project.md` | workflow-lifecycle init (full) |
| `tech-stack.md` | `.pi/tech-stack.md` | workflow-lifecycle init (auto-regenerated) |
| `roadmap.md` | `.pi/roadmap.md` | workflow-lifecycle init (`--context`) |
| `state.md` | `.pi/state.md` | workflow-lifecycle init (`--context`) |
| `user.md` | `.pi/user.md` | workflow-lifecycle init (`--user`) |
| `foundation-skill.md` / `foundation-capsule.md` | new skill/capsule leaves | workflow-lifecycle learn |
| `skill.md` | the mandated SKILL.md skeleton | workflow-lifecycle learn, writing-skills |
| `github-pr-ci.yml` | the project GitHub Actions quality workflow | `github-actions-engineering`, `push-pr` |
| `pull-request.md` | the PR body template | `push-pr`, project PRs |
| `readme.md` | the repository README | workflow-lifecycle init (new repos) |

## The 8 essentials (operating baseline)

File name = core principle:

1. `objectives.md` - purpose before process
2. `operating-philosophy.md` - the overall baseline
3. `stack-your-leverage.md` - mechanical checks before rules
4. `guiding-small-model.md` - write for small models too
5. `enforce-code-quality-mechanically.md` - inference + prevent
6. `how-to-build-good-tests.md` - what "good" means
7. `README.md` - index & how they fit

The pi-template repo ships mechanical gates (quality-gate, check-circular-deps,
check-integrity, repo-hygiene, conventional-commit, dead-code, run-inspo-tests)
that implement parts of these essentials; run them from the repo itself when
governing that repository. When proposing a new rule, first check whether the
right fix is a mechanical check, not just a behavioral prompt.
