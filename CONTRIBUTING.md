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

Skill names and descriptions should make selection clear. Keep names consistent
with their directory, references resolvable, and host-specific metadata valid for
the host that reads it. Search the skill files directly; generated catalogs and
static context budgets are not publication requirements.

## Pull requests

Describe the outcome, why it helps, checks actually performed, and compatibility
risks using `.github/pull_request_template.md`. Check changed-line whitespace with
`git diff --check` against the PR base. Do not claim model-routing improvements
were measured unless a comparison actually ran.

The remaining `scripts/pr-metadata.py` is repository automation: it parses PR
titles for the existing title check, labels, and release-note categories. It is
not used to consume this template. Its focused check is
`python3 scripts/pr-metadata.py --selftest`.

Required GitHub check names remain `quality / required` and `pr-title`; labels
are applied by repository automation. Workflow security is checked separately.
