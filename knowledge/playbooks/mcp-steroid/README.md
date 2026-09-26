---
title: mcp-steroid
summary: Use for the mandatory pre-PR IDE quality lane, or when an MCP-capable coding agent needs JetBrains semantic navigation, refactoring, inspections, tests, debugging, or a live-file witness.
kind: playbook
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

- **Use when:** validating any PR through `../pre-pr-validation/README.md`; inspect
 every changed path even when the diff is small or contains only prose/configuration.
- **Use when:** the question involves symbol resolution, types, usages,
 inheritance, overrides, call hierarchy, rename/move, change signature,
 inspections, project model, or debugger evidence.
- **Use when:** IDE UI control or automated refactoring is needed. The user does
  **not** need IntelliJ focused; a routed backend is enough.
- **Use when:** Sourcebot's indexed revision is behind HEAD (or the PR branch is
  unindexed) and you need a **live file witness** — read the bytes, do not treat
  Steroid as a second code-graph. Freshness rules live in
  [cross-repo-source](../cross-repo-source/README.md).
- **NOT when:** the change is trivial and direct source, compiler and tests settle
 it, and you are not validating a PR.
- **NOT when:** the IDE or backend is unavailable. Outside pre-PR validation, proceed
 with source, compiler and tests. During pre-PR validation, if no routed project path
 matches the repository, immediately notify the user of the exact repository path to
 open in IntelliJ (or a compatible JetBrains IDE with Steroid connected), then relist
 projects. The lane remains a recorded Blocker until the matching route is available.
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
4. **Targeted JetBrains semantic check**, inspect every changed path before a PR.
 For code, re-run usages, references or inspections on changed symbols and confirm
 no surprise callers. For prose/configuration, run applicable changed-file
 inspections and capture a live-file witness.
5. **Compiler/tests/runtime**, compile, run the relevant test suite, and any
 runtime probe; this is the finish gate.
6. **Finish**, report results; the compiler/tests/runtime verdict wins.

## Batch inspection sweeps

Sweeping many files with `runInspectionsDirectly` is the highest-yield use of this
lane, and a clean run over a real repository will not happen. Build the loop so one
broken file costs one file:

- **Crash-isolate every file.** A `try/catch` per path that prints `CRASHED: <message>`
  and continues is the difference between a 142-file sweep finishing and the whole
  script dying on file 3. Type-resolution faults (`ideGetElementType: Failed to find
  RemoteNode parent`, `Parent job is Cancelling`) are transport failures, not
  findings; when several files fail with the same message, treat the environment as
  flaky and keep going.
- **Read finding elements inside a read action.** `d.psiElement?.text` needs
  `readAction { … }` even though it only reads, because inspection results resolve
  their elements after the computation returns.
- **Keep batches near 20-25 files.** One call over 43 files exceeded the MCP request
  timeout; ~24 completed in minutes. Prefer several bounded calls to one maximal one.
- **Make output findings-only.** Print `clean` per path and cap each path at a few
  findings; this output is read by a model, not archived.
- **Refresh the route at call time.** After any IDE restart, calls fail with
  `project_name … is no longer present`. Read `steroid_list_projects` and pass the
  key it returns instead of a remembered one; the backend name changes with it.
- **Probe the channel before a large batch.** Run a trivial script
  (`println("ok")`) first when the IDE may be restarting or reindexing. Repeated
  timeouts on trivial code mean the backend is unavailable, not that inspections are
  slow; resume the sweep later instead of spending several long timeouts.
- **Expect modal dialogs.** While a modal IDE dialog is open, every remaining file
  fails with `waitForSmartMode requires a non-modal IDE`. Leading the script with
  `allowModalDialog()` resolves that (verified against IntelliJ 2026.2); the
  per-file crash line is the resume point for a tail that still failed.
- **Do not couple a sweep with evidence you need.** A long call that times out inside
  a batched program can discard sibling results; run verification greps separately.
- **Record partial coverage.** When the result carries `failedTools`, some inspections
  never ran. Check those files another way instead of reading silence as clean.
- **A ts-go-proxy fault does not end the run but buries the output.** On a type
  resolution fault the plugin prints a multi-KB `IDE Exception Captured` block
  inline (PSI dumps of the offending expression). Crash isolation survives it, and
  the file often inspects cleanly on a retry, but later lines can fall outside a
  bounded output view: re-read the tail before concluding a path was skipped.
- **Tag your own output and filter it.** Prefix every line the script prints (`SW|…`)
  and keep only those lines before reading the result. An inline exception dump then
  costs nothing, because it cannot crowd out findings inside a bounded view.

### Reading TypeScript unused-symbol findings

Unused-symbol findings over TS/TSX are unreliable without a call-site check. Verified
false-positive classes: object-literal dependency fakes in tests, command/RPC tables
dispatched by name, class members reached only through a structural interface, shim
modules substituted by bundler aliases (grepping the import path will not see them,
read the alias map), guard stubs written to throw if called, methods invoked through
a `#private` holder field (`this.#dialogs.hideVisible()` reads as unused), and
constructor parameter properties (`private readonly intervalMs`) read only inside
private methods, type-erased adapters (`asTerminalSessionService(...)`, where call
sites resolve to the interface instead of the concrete class), and `await expect(x)
.resolves/.rejects` chains (`ES6RedundantAwait` resolves only the sync `expect` type;
dropping that `await` loses the assertion).

Grep the symbol across every build-relevant root - `src`, `tests`, scripts,
workspace packages, examples, generated entrypoints - before deleting anything,
or ask a symbol-aware query instead of text. Keep the measurement honest:

- Do not exclude the owning module from the count. The heaviest caller of an
  exported class member is usually the class's own consumer in the same feature,
  and an exclusion like `grep -v controller.ts` turns five call sites into zero.
- Do not truncate the reference list with `head`; a "0 references" verdict from a
  capped list is an artifact. Count first, then read the hits.
- A single hit repo-wide means nothing else names the symbol textually - which is
  what a dead symbol looks like, not proof that it is one. Rule out the classes
  above first: dispatched by name, structural interface, type-erased adapter,
  alias or shim.
- Confirm the tree did not move under you. On a shared branch `git log <base>..HEAD`
  may list commits you did not author; a changed test count is explained by diffing
  normalized test names between runs (strip per-test timings) before blaming your own
  edit, and files those commits touched need a re-sweep before claiming coverage.

## Red Flags

- Skipping source reads "because the IDE knows", the IDE answers questions;
 source remains the authority.
- Letting a semantic check replace tests, inspections find style/latent
 issues, not behavioral regressions.
- Using the heavy endpoints (`steroid_take_screenshot`, `steroid_input`)
 when `steroid_execute_code` would do, save them for debugging UI flows.
- Trusting `project_name`/`backend_name` cached across IDE restarts,
 re-read `steroid_list_projects`.
- Retrying a dead routing key after `project_name … is no longer present`
 instead of listing projects again.
- Declaring Steroid down because `list_windows` or TS
 `runInspectionsDirectly` timed out while `list_projects` still routes.
 Use `modal: unleashed` + VFS bytes for a TS smell scan; `tsc` is the
 type gate.
- Blocking a `suspend` script with `runBlocking` or mutating PSI outside
 `readAction`/`writeAction`.
- Asking the user to open IntelliJ when a backend is already routed.

## Verification

- Open/verify the target project: `steroid_list_projects` shows the path. If it does
  not, notify the user to open that exact repository in IntelliJ, then relist; do not
  silently substitute another project. Frontendless backends skip the window gate. Do
  not wait on `steroid_list_windows` for a clean-code audit. Then await Maven/Gradle
  import only when the next call needs the index (`smartReadAction`, Java/Kotlin
  PSI). For TS/JS file bytes, VFS read is enough.
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
