---
title: pi-package-development
summary: Use when creating or modifying a Pi package, testing a local extension, auditing a published artifact, or diagnosing missing pi.dev listings. The installed Pi package docs own the contract.
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
The `pi-package` keyword makes an npm package eligible for gallery discovery;
it does not prove catalog visibility. Preview media are optional.
Pinned npm versions and Git refs do not move during ordinary package updates.
Use the delivery pack only for requested versioning, publishing or PR work.

For extension API changes, consult the installed `docs/extensions.md` and relevant
examples. Avoid copying those API contracts into a second guide.

## Diagnose publication and gallery visibility

Use this sequence when a package installs from npm but cannot be found on pi.dev.
Check the current [upstream package docs](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md)
for gallery requirements; do not assume an installed host's documentation
describes the current website implementation.

1. **Inspect the published artifact, not just the checkout.** Use
   `npm view <package> version dist-tags keywords pi peerDependencies repository gitHead maintainers --json`
   to identify the version under investigation. Fetch that exact version with
   `npm pack <package>@<version> --ignore-scripts --pack-destination <temporary-directory> --json`.
   Inspect its manifest, declared entry points and required runtime files.
   Do not install into the user's Pi configuration merely to inspect packaging.
   A checkout baseline and a CI-generated release version can differ legitimately;
   compare source identity using `gitHead` when provided.
2. **Check npm discovery separately.** Registry metadata and a downloadable
   tarball prove publication, not search indexing. Query npm's search API using
   the `pi-package` keyword and, when useful, the maintainer reported by npm:

   ```sh
   curl --fail --silent --show-error --get --max-time 30 \
     https://registry.npmjs.org/-/v1/search \
     --data-urlencode "text=keywords:pi-package maintainer:$MAINTAINER" \
     --data-urlencode "size=250"
   ```

   Set `MAINTAINER` from npm metadata, not the GitHub username. Inspect exact
   package-name matches and compare `total` with the returned count. An unscoped
   first page or quoted-name query can return unrelated results; a miss there
   does not establish absence. Narrow or paginate when an absence claim matters.
3. **Check both Pi surfaces.** Open the direct package detail page at
   `https://pi.dev/packages/<package-name>` and separately reproduce the catalog
   search using the site's current filter form. A real detail page should show
   the expected name, version, repository and install command, not merely return
   HTTP 200. A working detail page does not prove search visibility.
4. **Localize before changing anything.** If the published manifest meets the
   documented requirements, npm discovery returns the exact package, and Pi's
   detail page works while catalog search fails, report a catalog visibility
   discrepancy. This does not establish whether caching, filtering or indexing
   caused it. Do not invent a refresh deadline, submission requirement or
   popularity threshold, or republish solely to try to force discovery. Research
   an unresolved upstream implementation through the research pack; do not assume
   the website's indexer lives in the Pi core repository.

### Check the packaged README as a reader would

A Git-tree link check can pass while the same README breaks on npm or the gallery.
Check relative documentation links and images against the published tarball and
actual rendered URLs. Include required files in the payload, or use explicit
repository URLs for documentation intentionally kept outside the package. Inspect
optional `pi.image` and `pi.video` previews separately from README rendering;
missing previews are not a discovery blocker under the documented contract.

Keep presentation defects separate from listing failures. A missing linked
`SECURITY.md`, for example, needs a documentation or packaging fix but does not
by itself explain an absent search result. Preserve the existing README template
and a brief purpose and usage explanation when moving longer material to guides.

### Report the evidence by layer

State the tested version and source identity, artifact checks, npm search result,
Pi detail-page result and catalog-search result separately. A successful publish
job is not proof of immediate registry or gallery visibility. Name unresolved
boundaries and any untested installation behavior; do not imply a manifest or
link audit exercised the extension. Listing diagnostics do not authorize
publishing, changing npm metadata or installing packages into the user's host.
