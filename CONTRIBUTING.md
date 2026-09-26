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

Pack descriptions should make selection and legitimate composition clear. Packs
may compose when independent subproblems have different owners; each description
must state what that pack owns. Do not encode a fixed one-pack limit or an
exhaustive pairwise matrix.
Specialists live in `knowledge/playbooks/<name>/README.md` with `title`, `summary`,
and `kind: playbook` front matter, linked from one canonical pack index. Other
pack indexes may cross-link the same playbook; label those entries with the owning
pack. Only routers use `skills/<name>-pack/SKILL.md`. Keep references and helper
callers resolvable.

## Keep the template lean

Publish procedures with real consumers. Keep local experiments, session output,
completed plans, and host runtimes outside the template. Git preserves removed
material; do not create a replacement archive or generated inventory.

When a checkout supplies a host's live instructions, keep it on `main` and do
branch work in a separate Git worktree. After review and merge, reconcile the
live checkout with remote `main` without discarding local work. Switching the
live checkout to a feature branch changes the prompts the host consumes.

## Checks

Run the executable helper tests:

```sh
python3 knowledge/playbooks/pencil/scripts/test-verify-fidelity-manifest.py
node --test knowledge/playbooks/cdp/sdk/*.test.ts
```

The recording live test is opt-in: launch a disposable browser with remote
debugging and set `CDP_TEST_PROFILE_DIR` to its profile. Never point it at a
user's browser. A configured but unreachable profile fails; no profile reports
a named skip, not recording coverage.

For changes to the first-party mathematical sandbox, also run its pinned gate
and behavioral suite (Bend 2.0.27 and Python 3.10+):

```sh
python3 knowledge/playbooks/math-schema/bend/check.py
python3 -m unittest discover -s knowledge/playbooks/math-schema/bend/tests -v
```

The required CI job installs the official pinned Linux x64 Bend archive into
its temporary runner directory, checks its SHA-256 and runs both checks. For
an isolated local Linux x64 install, pass a new destination to
`bash knowledge/playbooks/math-schema/bend/tools/install-linux-x64.sh NEW_DESTINATION`
and prepend `NEW_DESTINATION/bend/bin` to `PATH`; existing destinations are
refused. The helper reads `bend-version` and `bend-linux-x64.sha256` from the
sandbox. Update the digest from the official release metadata when changing
the pin. It does not replace a host compiler or edit shell configuration.
Missing pinned-toolchain verification still blocks delivery of sandbox changes.

Check changed-line whitespace with `git diff --check` against the PR base.

Every PR runs the review lanes in `knowledge/playbooks/pre-pr-validation/README.md`
(project gates, CodeRabbit, IDE semantics, baseline and impact analysis, AI-slop
rejection). A lane that cannot run is a recorded blocker, not a skip.

## Pull requests

Describe the outcome, why it helps, the checks actually run, and compatibility
risks using `.github/pull_request_template.md`. Do not claim a check passed
unless it actually ran.
