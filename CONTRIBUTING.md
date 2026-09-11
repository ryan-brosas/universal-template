# Contributing

This repository publishes knowledge for coding agents, not an agent runtime.
Read and edit the relevant Markdown directly. There is no installation,
generation, catalog-validation, or custom publication pipeline to run.

## Review changes

Check that instructions help the task without imposing a model, provider, or
workflow. Keep tool-specific procedures scoped to that tool. Inspect changed
references, preserve useful source provenance, and avoid publishing credentials,
private configuration, or session artifacts. Test executable skill examples when
the change affects their behavior; use their existing focused tests.

Pack names and descriptions should make selection clear. Specialists belong in
`knowledge/playbooks/<name>/README.md` with `title`, `summary`, and `kind: playbook`;
link each from one pack index. Only routers use `skills/<name>-pack/SKILL.md`.
Keep references and helper callers resolvable, and verify the host's actual
discovery behavior. Use `templates/skill.md` for either content shape. Generated
catalogs and static context budgets are not publication requirements.

Keep prompts short and in natural language: they state the intent and leave
procedure and tool choice to the skills. Put workflows, tool calls, and report
formats in the owning playbook, and use `${ARGUMENTS:-}` when typed arguments must
reach the model.

## Keep the template lean

Publish reusable instructions, source evidence, and helpers with real consumers.
Keep local experiments, session output, completed plans, audit snapshots, and
host runtimes outside the template. Git preserves removed historical material;
do not create a replacement archive or generated inventory. Keep necessary
contracts beside their owning content and update callers when removing paths.

## Pull requests

Describe the outcome, why it helps, checks actually performed, and compatibility
risks using `.github/pull_request_template.md`. Check changed-line whitespace with
`git diff --check` against the PR base. Do not claim model-routing improvements
were measured unless a comparison actually ran.

The remaining `scripts/pr-metadata.py` is repository automation: it parses PR
titles for the existing title check, labels, and release-note categories. It is
not used to consume this template. Its focused check is
`python3 scripts/pr-metadata.py --selftest`.
`scripts/check-retired-paths.py` guards the removed context systems (Codebase
Memory, DeepWiki, foundations, the capsule library, the `api-design-practices`
alias, OpenViking); run `python3 scripts/check-retired-paths.py` before
completing a change here.

Required GitHub check names remain `quality / required` and `pr-title`; labels
are applied by repository automation. Workflow security is checked separately.
