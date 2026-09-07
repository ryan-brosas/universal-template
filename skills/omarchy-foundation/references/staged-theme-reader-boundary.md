# What can a palette reader assume during theme activation?

Source: `basecamp/omarchy` at `a9eaf7978e33a6832630c51f1bb87f97dbf5fe36`, MIT. Historical evidence, not a guarantee about later Omarchy versions.

## Flow and invariants

`bin/omarchy-theme-set:12-18` declares active state at `$HOME/.local/state/omarchy/current/theme` and a sibling `next-theme`. Names are checked at :283-291 before path construction. At :296-318, file descriptor 9 acquires flock, staging is removed/recreated, official material is copied, user material is overlaid or filtered, and missing palette/template files are generated.

At :337-341 the writer removes the active directory, moves staging to that name, then writes `theme.name`. This is serialized among cooperating writers, NOT an atomic replacement for independent readers. There is an observable missing-directory interval and the name file is a separate write. Readers must not use the name alone as proof the palette is present or unchanged. The lock is released at :361 before slower retint commands. A reader does not need permission to run those commands.

## Trust and failure boundaries

Installed git themes take `stage_installed_theme`; Lua, terminal launch configs, extension configuration and symlink escapes are filtered. User-written themes are treated differently. The distinction is provenance policy, not a sandbox. Palette consumption should remain data-only. A crash between remove and move can leave active state missing; the examined code is not a transactional rollback protocol. Watchers attached to the removed directory may need rebinding or polling.

## Direct tests

`test/shell.d/theme-staging-test.sh` builds temporary homes and invokes headless activation. Assertions cover installed theme color retention, prohibited executable config replacement by generated templates, symlink refusal, legacy Alacritty palette recovery, overlay filtering, user-authored exceptions, traversal names, and classification of generated template outputs. These establish staging trust policy; they do not prove concurrent reader consistency, crash recovery, or watcher rebinding. Source read directly, not executed; no upstream setup or dependencies installed.

## Active-project comparison

Heddlework `src/ui/theme-manager.ts:183-205` watches `dirname(path)`, falls back to polling on errors, and closes watchers idempotently. `omarchyThemePath` at :258-260 still selects the older config path. `tests/theme-omarchy.test.ts` checks injected watcher errors, polling fallback, cleanup, and that old XDG_CONFIG_HOME path. Those tests do not prove current upstream directory replacement works.

**Disposition: ADAPT.** Consume current state read-only, explicitly choose legacy-path compatibility, and test missing intervals/replaced-directory rebinding. Preserve last-good state or defaults by deliberate app policy; do not call Omarchy activation from the consumer.

## Retrieval and limits

Existing index `heddlework-inspo-omarchy`; this pass relies on direct source ranges and test assertions, not graph completeness. Scope is the writer/reader boundary only; excludes distro installation, compositor policy, and broad theming APIs. Current project requirements, tests, source and runtime behavior outrank this capsule.
