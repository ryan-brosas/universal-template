# Templates & essentials inventory

Installed globally at:

- `~/.agents/templates/` - the CLI-neutral format templates
- `~/.agents/essentials/` - the operating baseline docs

Canonical source: this repository (universal-template). Retired assets are
recoverable from Git history; there is no upstream repo to re-absorb from.
`catalog-quality.py` enforces this inventory against disk (templates and
essentials); `policy-consistency.py` keeps README and AGENTS from restating
counts or listing retired files as current.

## Format templates

13 CLI-neutral format templates:

`adr.md` `agents.md` `design.md`
`github-pr-ci.yml` `issue.md` `prd.md` `project-context.md` `proposal.md`
`pull-request.md` `readme.md` `roadmap.md` `skill.md` `tasks.md`

Plus `source.yml` (the inspo ledger; tracked separately from the format
templates).

Retired in the entry-architecture refactor (recoverable from Git history):
project.md, tech-stack.md, state.md, user.md — persistent project artifacts
are now selective (`project-bootstrap` Mode B / `goal-setup`), not a default
pack.

Usage mapping (what each rendered file's template drives):

| Template | Rendered into | Owner |
| --- | --- | --- |
| `agents.md` | project `AGENTS.md` | `project-bootstrap` (Mode B/C) |
| `project-context.md` | `docs/project-context.md` (or repo-native location) | `project-bootstrap` (Mode B, optional) |
| `roadmap.md` | roadmap doc | explicit user request only |
| `skill.md` | the SKILL.md skeleton | `writing-skills`, `leverage-capture` |
| `github-pr-ci.yml` | the project GitHub Actions quality workflow | `github-actions-engineering`, `push-pr` |
| `pull-request.md` | the PR body template | `push-pr`, project PRs |
| `readme.md` | the repository README | `project-bootstrap` (new repos) |

## The essentials (operating baseline)

File name = core principle:

1. `operating-philosophy.md` - the overall baseline
2. `steer-outcomes-not-behavior.md` - outcomes plus mechanical checks over behavior rules
3. `stack-your-leverage.md` - mechanical checks before rules
4. `guiding-small-model.md` - write for small models too
5. `enforce-code-quality-mechanically.md` - inference + prevent
6. `how-to-build-good-tests.md` - what "good" means
7. `openviking-foundation.md` - OpenViking holds durable experience, not source copies
8. `README.md` - index and how they fit

`discord-material/` holds the verbatim threads the essentials principles were
synthesized from.
The former objectives file moved to docs/roadmap.md — working objectives are
not cold rationale.

When proposing a new rule, first check whether the right fix is a mechanical
check, not just a behavioral prompt.
