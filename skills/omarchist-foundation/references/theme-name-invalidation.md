# Does theme-name polling detect same-theme palette edits?

Source: [tahayvr/omarchist](https://github.com/tahayvr/omarchist) at `d892f7d45cfe44a7692695254e2e035aee1f1051`, Apache-2.0. Historical evidence only.

## Entry, data and control flow

`src/system/ui_theme_watcher.rs:20-53` builds the older HOME/.config/omarchy/current paths and reads trimmed theme.name as Option<String>. `spawn_ui_theme_watcher` at :360-385 captures that name, waits one second, checks whether updating the app still works, then compares the current name with the captured name. Only inequality arms the thread-local `PENDING_UI_THEME_RELOAD` boolean and requests refresh.

`src/ui/app_view.rs:563-574` consumes the boolean during rendering, clears it before loading, calls `load_and_apply_omarchy_theme`, then refreshes windows. `ui_theme_watcher.rs:341-357` reads the palette, builds ThemeConfig, replaces the corresponding global dark/light theme, and changes mode. The source paths and these symbol names are the retrieval anchors.

## Invariants and failure boundaries

The invalidation key is the name, not palette bytes or modification time. Editing colors.toml while leaving the name unchanged cannot arm this loop's reload flag. Multiple changes before render coalesce to one boolean; loading reads current state rather than replaying every intermediate name. Clearing precedes loading, so it is not a retry queue.

A failed name read becomes None. A transition to None can trigger one refresh, but repeated None does not. The task exits when the app update fails; `.detach()` is not an explicit per-view cancellation handle. Rendering owns consumption while the app-global theme owns the result. Missing palette input skips application; theme parsing/config defaults are separate policies. The older path is not current Omarchy contract authority.

## Tests and evidence limits

No inline test exists in the examined watcher file, and the bounded source search did not locate a direct watcher test. This is a source-derived failure model, not demonstrated upstream runtime behavior. Do not substitute unrelated Omarchist configuration/version tests.

Heddlework `tests/theme-omarchy.test.ts`, `refreshes Omarchy colors while an explicit theme mode is selected`, changes the injected palette without any theme-name change and observes one notification. `polls when the Omarchy watcher is unavailable beside a live system monitor` demonstrates palette refresh through fallback polling; asynchronous watcher-error and disposal tests cover their injected lifecycle. These local tests passed, not the upstream watcher.

## Local comparison and disposition

Heddlework `src/ui/theme-manager.ts:101-110` reads an overlay and compares a stable sorted palette key, not theme.name. At :113-138 disposal reverses cleanup and stops polling. Native directory-replacement behavior still needs separate verification.

**Disposition: OMIT.** Do not adopt name-only invalidation for Heddlework: it would miss same-theme palette edits already covered by the local test. Preserve this source-specific counterexample to distinguish a display label from a content-version key. This does not reject Omarchist's unrelated palette derivation.

## Scope

One polling-to-render invalidation path. Current project requirements, tests, source and runtime behavior outrank this projection. Upstream tests and live GPUI execution were not run; no setup or re-indexing. Existing full index: `heddlework-inspo-omarchist`. Re-read the cited source before relying on this historical behavior.
