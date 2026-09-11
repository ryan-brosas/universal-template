# Contributing

This repository publishes reusable instructions for coding agents, not an agent
runtime. Edit the Markdown directly; there is no installation, generation, or
publication pipeline.

## Review changes

Check that instructions teach a reusable way of working and stay model-agnostic:
no model ranking, provider routing, or execution framework. Keep tool-specific
procedures scoped to that tool. Retrieve repository information from source
instead of storing summaries. Avoid publishing credentials, private
configuration, or session artifacts.

Pack descriptions should make selection clear. Specialists live in
`knowledge/playbooks/<name>/README.md` with `title`, `summary`, and
`kind: playbook` front matter, linked from one pack index. Only routers use
`skills/<name>-pack/SKILL.md`. Keep references and helper callers resolvable.

## Keep the template lean

Publish procedures with real consumers. Keep local experiments, session output,
completed plans, and host runtimes outside the template. Git preserves removed
material; do not create a replacement archive or generated inventory.

## Checks

Run the executable helper tests:

```sh
python3 knowledge/playbooks/pencil/scripts/test-verify-fidelity-manifest.py
node --test knowledge/playbooks/cdp/sdk/recording-privacy.test.ts
```

Check changed-line whitespace with `git diff --check` against the PR base.

## Pull requests

Describe the outcome, why it helps, the checks actually run, and compatibility
risks using `.github/pull_request_template.md`. Do not claim a check passed
unless it actually ran.
