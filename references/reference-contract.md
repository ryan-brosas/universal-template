# Reference Contract — project-local implementation prior art

The single contract for using external repositories as prior art. Procedures
live in `skills/codebase-driven-development`; this file owns the rules.

## Purpose

Reference repositories provide **working implementation prior art**: real
source and real tests to study, port from, and compare against.

## Location

`<project>/reference/<repo>/` — one directory per reference repository.

## Authority

A reference repository is **evidence**, not authority: the current project's
requirements and tests are the acceptance authority. The reference shows how
someone else solved a similar problem; this project decides what ships.

## Defaults

- **One reference first.** Add a second only after naming the specific gap the
  first left open. Do not search ten repositories when one closes the gap.
- Read the actual reference source and its direct tests; documentation and
  summaries are leads, not evidence.
- Decide **ADOPT / ADAPT / OMIT** per boundary, with provenance (repo, path,
  revision) recorded in the PR's Reference / Prior Art section.

## Tool roles against a reference

- **Fovea** — map the reference root (`fovea_sketch` / `fovea_focus`) when
  structural orientation helps; then read exact source windows.
- **Steroid / JetBrains** — exact semantics (types, usages, inheritance) when
  deeper investigation helps; also the runtime lane (debugger, tests).
- **Codebase Memory** — *discovery*: which persistent-library project likely
  contains the pattern. Once identified, activate it under `reference/` and
  inspect with Fovea/source. The graph is an index, not source of truth.
- **OpenViking** — learned experience about the approach (what failed before,
  why), never a substitute for reading the reference source.
- **Veda** — advisory reasoning on a hard port; verify against evidence.

## Skills

Do not automatically turn reference repositories into skills or foundations.
A foundation is the selective exception for repeated, non-obvious porting
knowledge (`skills/code-foundations` promotion rule); repository → foundation
generation is frozen by default while this contract is the standard path.

## License

When materially copying implementation, inspect the upstream license and
preserve required attribution (record it in the PR's Reference / Prior Art
section).

## Lifecycle

References are normally read-only, local, and disposable. Prefer
`.git/info/exclude` for local-only references instead of the shared
`.gitignore`; a reference is not automatically committed, skilled, indexed by
CodeMemory, or ingested into OpenViking.
