---
title: pi-package-development
summary: Use when creating or modifying a Pi package, its resource manifest or dependency layout, or testing a local extension with pi -e. The installed Pi package docs own the contract.
kind: playbook
---

# Developing Pi packages

Use the installed package documentation at
`~/.bun/install/global/node_modules/@earendil-works/pi-coding-agent/docs/packages.md`
for the current contract. Reuse it during the task; check again when the installed
version changes or an unresolved behavior needs investigation. This procedure is
for packages and extensions, not Pi core development or generic npm libraries.

## Inspect the existing package

- Resolve which source and build artifact Pi actually loads before editing.
  Source tests do not establish that the installed extension contains the fix.
- Preserve the existing resource layout. An explicit `pi` manifest is useful for
  nonstandard paths and filtering; conventional directories work without one.
  Manifest paths are package-relative. Settings filters only narrow the manifest.
- Keep third-party runtime dependencies declared. Imported host packages belong
  in `peerDependencies` with `"*"`, not bundled copies: `pi-ai`, `pi-agent-core`,
  `pi-coding-agent`, `pi-tui` (under `@earendil-works/`) and `typebox`.
- Other Pi packages used as dependencies need their resources in the tarball,
  normally through `bundledDependencies`. Do not assume separate extensions share
  dependency instances or can resolve one another's undeclared dependencies.

## Test and activate deliberately

Run the package's focused tests and required build. Inspect its manifest, exported
paths and packaged files using existing tooling; do not create another validator
just to restate the specification.

`pi -e /absolute/package/path` tries an extension for one invocation. Use
`--no-extensions` to exclude configured extensions when an isolated load is
needed; explicit `-e` paths still load. Exercise the affected behavior through
the host as well as its tests, and state any untested terminal or RPC behavior.

`pi install <source>` persists a declaration. Global and project settings have
different scopes; a local-path declaration and an npm declaration have different
identities even if they contain the same package. When switching sources, replace
the intended declaration rather than accidentally loading both. Keep a rollback
path and distinguish configured changes from changes active in a running session.

For publication, include every runtime resource in the package's `files`/tarball.
The `pi-package` keyword enables gallery discovery; preview media are optional.
Pinned npm versions and Git refs do not move during ordinary package updates.
Use the delivery pack only for requested versioning, publishing or PR work.

For extension API changes, consult the installed `docs/extensions.md` and relevant
examples. Avoid copying those API contracts into a second guide.
