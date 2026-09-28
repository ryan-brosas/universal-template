---
title: fallow
summary: Use when investigating unused files, exports or dependencies, duplication, complexity or change impact in JS/TS; Fallow supplies candidates to inspect, not a verdict on code quality.
kind: playbook
---

# Fallow: static-analysis evidence

Use Fallow when a JS/TS cleanup or review needs its analysis. It is not a
prerequisite for every edit or code-quality claim, and it does not analyze
Markdown instructions. If it is unavailable, use the project's existing tooling
and direct source inspection; report the coverage limit rather than installing
it or inventing output.

## Choose the relevant analysis

Confirm the installed version's help and the project's entry points, workspaces
and configuration. Use JSON when consuming structured results. Run the analysis
that answers the question, not every command by default:

```sh
fallow dead-code --format json
fallow dupes --format json
fallow health --format json
```

For change impact, choose the repository's actual comparison ref and use
`fallow audit --changed-since <base-ref> --format json`. The placeholder is not a
literal branch name. Run before and after a cleanup when comparison informs the
result, keeping the scope and configuration comparable.

## Investigate before changing code

Treat findings as candidates. Inspect the named source and its consumers,
including public package exports, framework entry points, dynamic imports and
side effects. Syntactic analysis cannot settle every runtime or external use.
A local absence of imports is not proof that a published API is unused.

Explain each proposed deletion or simplification in terms of behavior and
maintenance cost. Duplication does not automatically justify extraction, and a
complexity score does not automatically justify splitting a function. Preserve
load-bearing code and explain false positives instead of changing code just to
improve a score.

Keep edits within the authorized cleanup. Report-only work stops at findings.
Do not apply automated fixes without inspecting the proposed changes and their
consumers; never suppress a real issue merely to make the report green.

## Verify the outcome

Read the final diff and exercise the affected behavior with the project's
relevant tests and type checks. Re-run applicable analysis to understand changes
in findings, not to claim the application works. Report the source evidence,
checks actually run and any unresolved consumers or runtime paths.

## References

Load only the relevant section:

- [CLI reference](references/cli-reference.md): command and output details;
  installed help owns version-specific behavior.
- [Gotchas](references/gotchas.md): analysis limits, configuration and exit codes.
- [Patterns](references/patterns.md): a requested integration or larger workflow,
  not prerequisites for a local investigation.
