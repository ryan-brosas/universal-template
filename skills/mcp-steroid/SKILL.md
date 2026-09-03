---
name: mcp-steroid
disable-model-invocation: true
description: Use when an MCP-capable coding agent needs native JetBrains IntelliJ APIs, semantic navigation, refactoring, inspections, tests, debugging, or IDE UI control.
---

# MCP Steroid, JetBrains semantic layer

## Core Principle

JetBrains is a **semantic quality layer**, not a replacement for source reads,
the compiler, or tests. The IDE has indexed the project: it answers usages,
symbol resolution, types, inheritance, overrides, call hierarchy, inspections,
and project-model questions precisely. Use it as a preflight before editing and
as a targeted check after; keep the normal loop (inspect → implement →
compiler/tests/runtime) intact.

## When to Use / NOT

- **Use when:** the question involves symbol resolution, types, usages,
 inheritance, overrides, call hierarchy, rename/move, change signature,
 inspections, project model, or debugger evidence; or when the change is
 non-trivial and the IDE is open on the project.
- **Use when:** IDE UI control or automated refactoring is needed.
- **NOT when:** the change is trivial (a rename in one file, a comment, a
 config tweak), the compiler and tests cover it.
- **NOT when:** the IDE/backend is unavailable, proceed with source,
 compiler, and tests; JetBrains is optional.
- **NOT when:** you need execution or orchestration, that is Fabric/agents;
 MCP Steroid is the semantic/IDE lane only.

## Workflow

1. **Inspect** the code: read the file, Fovea the working set, confirm the
 change boundary in source and tests.
2. **JetBrains semantic preflight (when useful)**, confirm intent and blast
 radius with semantic evidence:
 - resolve symbols and types; walk call hierarchies; list overrides;
 - confirm no hidden callers before rename/move/signature changes;
 - run inspections over the target range to surface latent issues.
 Use it to steer the edit, not to skip reading the code.
3. **Implement** the change with normal tools.
4. **Targeted JetBrains semantic check (when useful)**, re-run usages,
 references, or inspections on the changed symbols; confirm no surprise
 callers and that the intended contract holds.
5. **Compiler/tests/runtime**, compile, run the relevant test suite, and any
 runtime probe; this is the finish gate.
6. **Finish**, report results; the compiler/tests/runtime verdict wins.

## Red Flags

- Skipping source reads "because the IDE knows", the IDE answers questions;
 source remains the authority.
- Letting a semantic check replace tests, inspections find style/latent
 issues, not behavioral regressions.
- Using the heavy endpoints (`steroid_take_screenshot`, `steroid_input`)
 when `steroid_execute_code` would do, save them for debugging UI flows.
- Trusting `project_name`/`backend_name` cached across IDE restarts,
 re-read `steroid_list_projects`.
- Blocking a `suspend` script with `runBlocking` or mutating PSI outside
 `readAction`/`writeAction`.

## Verification

- Open/verify the target project: `steroid_list_projects` shows the project,
 `steroid_list_windows` reports `modalDialogShowing=false`,
 `indexingInProgress=false`, `projectInitialized=true` (frontendless
 backends skip the window gate), then await the Maven/Gradle import before
 semantic queries.
- After `steroid_execute_code`, read the printed results, output is the only
 way to observe the script.

## References

- `references/api-manual.md`, full IntelliJ API manual: tool semantics,
 Kotlin patterns, PSI/VFS recipes, Rider notes, available
 `mcp-steroid://` resources. Load on demand; runtime tool schemas document
 each call.
- Runtime resources: `mcp-steroid://skill/*` (power-user, debugger,
 test-runner guided recipes), `mcp-steroid://test/overview`,
 `mcp-steroid://ide/overview` for copy-able patterns.
