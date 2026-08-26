# Templates & essentials inventory

Installed globally at:

- `~/.agents/templates/` — 15 CLI-neutral format templates
- `~/.agents/essentials/` — the operating baseline docs (8)

Source: the pi-template repo (`~/.agents (absorbed from the retired pi-template repo)`); re-absorb
from it on demand to keep these current.

## The 15 format templates

`adr.md` `agents.md` `design.md` `foundation-skill.md` `foundation-capsule.md`
`issue.md` `prd.md` `project.md` `proposal.md` `roadmap.md` `skill.md`
`state.md` `tasks.md` `tech-stack.md` `user.md`

Usage mapping (what each rendered file's template drives):

| Template | Rendered into | Owner |
| --- | --- | --- |
| `agents.md` | `AGENTS.md` | /init full |
| `project.md` | `.pi/project.md` | /init full |
| `tech-stack.md` | `.pi/tech-stack.md` | /init full (auto-regenerated) |
| `roadmap.md` | `.pi/roadmap.md` | /init (`--context`) |
| `state.md` | `.pi/state.md` | /init (`--context`) |
| `user.md` | `.pi/user.md` | /init (`--user`) |
| `foundation-skill.md` / `foundation-capsule.md` | new skill/capsule leaves | `/learn` |
| `skill.md` | the mandated SKILL.md skeleton | `/learn`, writing-skills |

## The 8 essentials (operating baseline)

File name = core principle:

1. `objectives.md` — purpose before process
2. `operating-philosophy.md` — the overall baseline
3. `stack-your-leverage.md` — invest where returns compound
4. `steer-outcomes-not-behavior.md` — mechanical checks before rules
5. `guiding-small-model.md` — write for small models too
6. `enforce-code-quality-mechanically.md` — inference + prevent
7. `how-to-build-good-tests.md` — what "good" means
8. `README.md` — index & how they fit

The pi-template repo ships mechanical gates (quality-gate, check-circular-deps,
check-integrity, repo-hygiene, conventional-commit, dead-code, run-inspo-tests)
that implement parts of these essentials; run them from the repo itself when
governing that repository. When proposing a new rule, first check whether the
right fix is a mechanical check, not just a behavioral prompt.