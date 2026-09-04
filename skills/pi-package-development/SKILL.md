---
name: pi-package-development
description: "Use when creating, editing, structuring, testing, or shipping a pi package or pi extension (package.json pi manifest, pi-package keyword, peerDependencies, bundling, pi install -e testing, gallery metadata) — encodes the packages.md contract. Trigger-first; pick over generic npm-package advice."
invocation: entry
---

# Developing pi Packages

## Core Principle
A pi package is an npm/git package with a `pi` manifest declaring resources. The contract lives in the local docs — re-read it before structural changes; this skill is the checklist, not the spec.

## When to Use / NOT
- **Use when:** creating or modifying a pi package (extensions, skills, prompts, themes); wiring `package.json` for pi; testing with `pi -e` / `pi install`; publishing.
- **NOT when:** building non-package npm libraries; pi CLI core development (repo, not package).

## Workflow
1. **Re-read the spec:** open the local docs file (References) — it is authoritative and versioned with the installed pi.
2. **Manifest:** add a `pi` key to `package.json` — `"extensions"`, `"skills"`, `"prompts"`, `"themes"` arrays, relative to package root, globs and `!exclusions` allowed. No manifest? Conventional dirs (`extensions/`, `skills/`, `prompts/`, `themes/`) are auto-discovered.
3. **Discoverability:** include `"pi-package"` in `keywords` (gallery: pi.dev/packages). Optional `pi.video` (MP4) / `pi.image` (PNG/JPEG/GIF/WebP) preview fields; video wins if both.
4. **Dependencies rule (the common mistake):**
   - Third-party runtime deps → `dependencies` (pi runs `npm install` on package install).
   - Core pi packages — `@earendil-works/pi-ai`, `@earendil-works/pi-agent-core`, `@earendil-works/pi-coding-agent`, `@earendil-works/pi-tui`, `typebox` — import freely but list in `peerDependencies` with `"*"` and never bundle them.
   - Other pi packages → `dependencies` + `bundledDependencies`, reference via `node_modules/<pkg>/...` paths.
5. **Dev loop:** `pi -e /abs/path/to/pkg` loads a one-off without installing; `pi install <source>` persists (user vs `-l` project settings); `pi config` toggles resources; `pi list` shows installs.
6. **Stop condition:** manifest valid, keyword set, dependency tiers correct, package loads via `pi -e`.

## Red Flags
- **HARD-GATE:** never put core pi packages (`pi-ai`, `pi-agent-core`, `pi-coding-agent`, `pi-tui`, `typebox`) in `dependencies` or bundle them — `peerDependencies` with `"*"` only.
- Do not ship resources outside `files`/the tarball — an extension importing a file npm did not pack breaks on install.
- Dot-prefixed resources are not glob-discovered; list them directly in the manifest.
- Pinning a git source ref is intentional (`pi update` never moves it); use `pi install git:host/user/repo@new-ref` to move it.
- Settings filters (object form) only narrow what the manifest allows — they cannot add resources.

## Verification
- `bun -e` script asserting: `pi` manifest present, `pi-package` keyword, entry files exist, core packages in `peerDependencies` with `"*"` and absent from `dependencies`, `files` complete.
- Load the package: `pi -e <path>` and exercise the extension in a session.

## References
- `~/.bun/install/global/node_modules/@earendil-works/pi-coding-agent/docs/packages.md` — the spec (mirrors https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md).
- `~/.bun/install/global/node_modules/@earendil-works/pi-coding-agent/docs/extensions.md` — extension API surface.
