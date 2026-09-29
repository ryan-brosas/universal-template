---
title: mcp-steroid
summary: Use for explicitly opted-in JetBrains semantic navigation, refactoring, inspections or debugging. Not a default verification dependency or a required pre-PR lane.
kind: playbook
---

# MCP Steroid

## Scope

Steroid is an optional IDE integration, not a replacement for source reads,
compilers or tests. Use it when the project or user opts in and the task needs
symbol resolution, usages, call hierarchies, rename/move/signature refactoring,
project-model diagnostics or debugging. A multilingual repository needs coverage
from its relevant language tools; one IDE index does not establish that coverage.

Do not activate it for routine edits, prose/configuration validation or merely
because Sourcebot's index is stale: local file reads establish current bytes.
If optional IDE evidence is unavailable, continue with sufficient local checks.
If the task explicitly requires it, report the gap without silently substituting
another project. [Activation](../../../mcp/catalog.md#optional-ide-integration)
belongs in project configuration, not a universal PR checklist.

## Workflow

1. Read the affected source and define the question the IDE should answer.
2. Call `steroid_list_projects`; match the repository's path and retain its opaque
   `project_name` routing key. Refresh it after a backend restart. Do not reuse a
   similarly named project or confuse the display name with the routing key.
3. If no route matches, report the missing project. Open it only within the
   authorized IDE task. A routed headless backend is sufficient; do not require
   desktop focus or a frontend window. Project routing is not proof of indexing:
   await Maven/Gradle import when the next operation requires its semantic model.
4. Discover current schemas and load only the relevant `mcp-steroid://` recipe.
   Keep `smart_non_modal` for semantic work. Respect read/write actions, and use
   `smartReadAction` for indexed reads. Do not bypass a blocked modal state to force
   an inspection; pause for user interaction when necessary.
5. Query or refactor the bounded symbols, then inspect the actual diff. Recheck
   affected references/diagnostics where useful; no every-file IDE sweep is
   required. Read the printed results from `steroid_execute_code`: a successful
   call with no output does not establish the intended result.
6. Run relevant compiler checks, tests and runtime probes. Report the IDE's actual
   coverage and limitations separately from behavioral verification.

Use screenshots and input tools only for an authorized UI problem, not routine
semantic work. No window-status gate is needed for headless inspections or VFS
file reads. Repeated timeouts on a trivial script indicate a backend problem;
stop retrying instead of spending several full request timeouts.

## Batch inspections, when warranted

- Isolate failures per path and report them. Transport/type-resolution faults
  such as `RemoteNode parent` or `Parent job is Cancelling` are not code findings.
- Keep batches bounded. Prior TS sweeps completed around 20–25 files per call
  while 43 exceeded the timeout; size for the current backend and file cost.
- Read finding elements such as `d.psiElement?.text` inside a read action.
- Tag your printed output (for example `SW|`) so inline plugin exception dumps
  do not crowd out findings. Report clean paths and cap displayed findings without
  claiming the cap is complete coverage. Inspect the tail when output is truncated.
- Treat `failedTools`, crashed files and timeouts as partial coverage, never clean
  results. Keep independent verification out of a long call whose timeout could
  discard sibling results.

## TypeScript unused-symbol findings

Confirm call sites before deleting symbols. Known false-positive classes include:

- test dependency fakes, guard stubs and command/RPC tables dispatched by name;
- members reached through structural interfaces or type-erased adapters;
- shim modules selected by bundler aliases;
- methods invoked through a `#private` holder and constructor parameter properties
  read only from private methods;
- `await expect(...).resolves/.rejects`: an `ES6RedundantAwait` finding can resolve
  only the synchronous `expect` type; dropping the await loses the assertion.

Search all build-relevant roots, including tests, scripts, workspace packages,
examples and generated entrypoints; inspect dispatch and alias maps too. Include
same-file consumers and do not infer a reference count from a truncated list.
A single textual hit is not proof of dead code. Confirm the working tree has not
changed since the inspection before reusing its coverage.

## References

- [API recipes](references/api-manual.md): read the relevant Kotlin/PSI/VFS or Rider
  section only. Current runtime schemas and resources own tool contracts.
- `mcp-steroid://skill/*`, `mcp-steroid://test/overview` and
  `mcp-steroid://ide/overview`: task-specific execution, debugger and test recipes.
