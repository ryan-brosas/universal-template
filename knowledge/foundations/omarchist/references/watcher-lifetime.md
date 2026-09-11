# Who can stop Omarchist's theme watcher?

Source: [tahayvr/omarchist](https://github.com/tahayvr/omarchist/tree/d892f7d45cfe44a7692695254e2e035aee1f1051), `d892f7d45cfe44a7692695254e2e035aee1f1051`, Apache-2.0. Checkout `<local-checkouts>/omarchist`; origin and HEAD reverified, working tree clean. Current project source, requirements, tests and runtime behavior outrank this historical evidence.

## Question and flow

Can a window or feature owner withdraw polling without shutting down the application? This is a lifecycle question, separate from whether a name change detects palette edits.

- `src/main.rs:113-119` applies the initial theme and starts the watcher at application startup.
- `src/system/ui_theme_watcher.rs:15-18,360-383`: `spawn_ui_theme_watcher` returns no task handle. It starts an app task and detaches it. Each loop waits one second, then attempts an empty app update. An update error breaks the loop before the next filesystem read. Successful updates permit name sampling, pending-flag mutation and app refresh.
- `src/ui/app_view.rs:564-574` consumes and clears the thread-local boolean during rendering, applies the theme and refreshes windows. This is a coalesced invalidation, not one queued application per name change.

## Ownership and failure limits

The explicit stop condition is loss of the app update context, not closure of a particular window or disabling a feature. The inspected API gives callers no cancellation handle and contains no start-once guard. Repeated calls can therefore create multiple polling tasks by source inference; this was not reproduced in a running application. Window-close behavior is not established by the shutdown check. Detachment is deliberate app-lifetime ownership, not evidence of reversible plugin ownership.

The refresh result is ignored. A pending flag can survive until a later render; successful sampling does not prove immediate display. This pass does not inspect GPUI executor shutdown internals or prove a one-second termination deadline.

## Direct tests and local comparison

No `#[test]` or `#[cfg(test)]` occurs in the examined watcher module. No direct watcher cancellation test was located. Upstream was not built or executed.

Heddlework's `src/ui/theme-manager.ts:94-132,135-174` uses idempotent `start`, a tracked timer, and a LIFO cleanup list. `dispose` clears the timer, withdraws attached sources and clears subscribers. That ownership fits independently unloadable features better than an unreturned detached task. It is not proof against already-retained callbacks: the data callback calls `refreshSystemTheme` without a started-state fence.

`tests/theme-omarchy.test.ts:62-100,219-234` was read directly. The polling test calls start/dispose but only asserts the snapshot; it does not measure future timer quiescence. The monitor-error test checks fallback and one SIGTERM; the watcher test checks disposal. The full module passed **11 tests / 25 assertions**, exit 0. These tests establish local injected boundaries, not Omarchist runtime cancellation.

## Disposition

**OMIT** the detached app-lifetime watcher as a reusable Heddlework feature lifecycle. Keep an explicit cleanup owner; do not import a second polling loop or assume window destruction ends an application task.

## Next question and limits

Next: how do missing versus malformed palette fields affect render-time fallback? This pass stops at watcher ownership; palette derivation is not newly covered. Direct source navigation only, no graph refresh, dependencies, desktop scripts, app changes or native execution.
