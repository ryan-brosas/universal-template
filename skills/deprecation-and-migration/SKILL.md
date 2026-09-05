---
name: deprecation-and-migration
description: Use when deprecating APIs, migrating between library versions, removing legacy code, or planning breaking changes, covers deprecation notices, migration guides, codemods, and staged rollout
invocation: entry
---

# Deprecation and migration

Start with the consumers and compatibility contract. A public API with unknown
consumers needs notice and a usable replacement; a private helper whose callers
are changed together may need neither a deprecation period nor a migration guide.
Use the project's release policy for timing and versioning. There is no universal
three-month wait, one-break-per-major rule, or requirement for parallel paths.

## Give consumers a usable path

For published APIs, say what replaces the old behavior, what changes semantically,
and when removal is intended. Put the notice where affected consumers will see
it: type annotations, release notes, docs or bounded runtime warnings as fits
the interface. Do not add noisy runtime logging merely to duplicate a type notice.

```ts
/**
 * @deprecated since 2.3.0. Use newApi() instead.
 * Planned removal: 3.0.0. See the 2.3 migration guide.
 */
```

A migration note often needs only the smallest before/after example and the
non-obvious semantic differences. Add rollout, rollback or mixed-version
compatibility details when data, distributed deployments or external consumers
make them consequential. A feature flag is one option, not a required layer.

## Automate repetition, not ambiguity

A codemod earns its place for repeated, reliably identifiable transformations.
Prefer an existing upstream migration tool. If authoring one, resolve imported
bindings rather than renaming every call with the same spelling; preserve
comments and unrelated code, and leave ambiguous cases for review. Check real
call sites, alias/shadowing cases, and a second run for unintended further edits.
Small migrations may be safer as direct edits. Inability to automate a semantic
change is not a reason to forbid the migration.

Verify the new path through actual consumers. During a promised compatibility
window, test the old path too; after removal, check exports, registrations and
remaining callers. For data migrations, exercise retry/interruption and recovery
where those risks exist. Report incompatibilities rather than inferring safety
from compilation alone.
