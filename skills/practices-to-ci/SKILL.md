---
name: practices-to-ci
description: "Use when a recurring, objective failure may deserve an automated check; reuse existing project gates before adding a custom validator or CI step."
invocation: internal
disable-model-invocation: true
---

# Turn an earned constraint into a check

A deterministic property is a candidate for automation, not an obligation to
build a script. The check should prevent a real failure for less effort than it
adds in maintenance, runtime and false positives. Leave architectural taste,
prose quality and whether the agent followed a preferred process to judgment.

Look for an existing compiler option, test, formatter, linter, schema validator
or repository rule that already owns the boundary. Extend it instead of
creating a parallel gate. A custom helper is useful when the repository has a
specific invariant that those tools cannot express; use the project's language
and conventions, not a template-mandated `scripts/*.py` layout.

Before wiring a new check into CI, try a representative violation and valid
input, including legitimate exceptions. Diagnostics should identify the failed
contract without echoing secrets. A check that passes the current repository
can still be useful; demonstrate its catch with a safe fixture or mutation.

`../test-generation/SKILL.md` covers catch-first test design.
`../github-actions-engineering/SKILL.md` covers workflow integration when needed.
This skill carries no template-specific CI inventory; the repository's own
configuration is the authority for what runs.
