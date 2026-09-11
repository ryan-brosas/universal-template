# Which validation gates precede accepted update staging?

Source: [egoist/waku](https://github.com/egoist/waku) at `1114d4c5bdd3baf1454667bd7dd73ddd767a4767`, GPL-3.0-only. Architecture-only evidence, not implementation text for copying.

## Entry and control flow

`src/updater/linux.rs:389-418`, `fetch_and_stage`, obtains a feed item, rejects absence, returns None for a non-newer version, validates version and URL, and requires a positive bounded declared length. It allocates a unique staging sibling under a StagedUpdate guard, downloads with a byte limit, compares actual length, verifies the archive signature, extracts, removes the archive, and validates the packaged layout before returning Some(staged).

`verify_archive` (:420-438) decodes the signature/key and calls strict verification on archive bytes before extraction. `extract_release_archive` (:440-505) checks entry count, exact version-and-target root, normal path components, duplicate relative paths, file/directory entry types, checked cumulative unpacked size and maximum size before unpacking. Links and special entries are rejected. These are separate defenses: a valid signature is not a filesystem-path policy.

`validate_packaged_layout` (:507-524) requires a regular managed-marker file with exact content and three regular executable files. It does not validate every desktop/icon/license file staged by the packaging script, so do not call it an exhaustive artifact manifest check.

## Ownership and failure boundaries

`StagedUpdate` and its Drop implementation (:107-137) retain an optional staging path. Early error drops the guard and attempts recursive cleanup; cleanup errors are ignored. `disarm` takes the path out for handoff, so normal drop no longer deletes transferred state. This is best-effort RAII cleanup, not crash recovery or transactional installation. Failed extraction may leave partial files until cleanup runs. Updater installation, process handoff and rollback are outside this capsule.

## Direct tests

Read :790-837: `the_embedded_public_key_is_usable` validates key construction only; `release_versions_cannot_become_paths` rejects traversal, slash-bearing and empty versions while accepting a prerelease; `extraction_strips_only_the_expected_release_root` builds a valid archive and checks extracted app bytes and packaged layout.

Despite its name, the extraction test does not supply a wrong root, duplicate, link, traversal entry, oversized expansion or invalid signature. The guards above are source-confirmed, not adversarial-test-proven. Upstream tests were read, not executed; no dependencies or setup ran.

## Heddlework comparison

`scripts/build.ts:26-65` compiles the platform output; the shown staging cleanup is for macOS CEF packaging. `tests/window-options.test.ts` checks Linux desktop Icon/StartupWMClass against appId but is not an archive-install test. No equivalent signed Linux update pipeline is asserted here. Heddlework's artifact/runtime requirements must define its own accepted layout.

**Disposition: ADAPT.** Preserve validation-before-handoff and explicit staging ownership as design evidence if Heddlework adds Linux update staging. Define its own manifest, trust roots and negative tests; do not import Waku's GPL implementation, daemon layout or product-specific marker.

## Retrieval and scope

Existing full index: `heddlework-inspo-waku`. Search the named functions, then read the ranges and tests at the pinned source. This pass used direct source, not graph completeness claims. Current project source, tests, requirements and runtime behavior outrank this historical projection. No network download, extraction probe or live update was executed.
