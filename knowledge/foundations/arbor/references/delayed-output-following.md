# Can delayed output following override a user's scroll or target a different terminal?

Source: [penso/arbor](https://github.com/penso/arbor/tree/d8d82b7eec6cba3682374875d8f13407c7181ef0), revision `d8d82b7eec6cba3682374875d8f13407c7181ef0`, MIT. Origin/HEAD match the approved checkout, which was clean. Upstream freshness beyond that pin was not checked. Current project source, tests, requirements and runtime behavior outrank this historical projection.

## State and entry points

`crates/arbor-gui/src/terminal_interaction.rs:52-85`, `request_terminal_scroll_to_bottom`, scrolls, enables sticky following, sets a 48 ms deadline, and records the current extent. `notify_after_terminal_input` (:237-257) enables sticky following and schedules only when its input session is active. `constants.rs:98-105` defines a 16 ms scheduled delay, 48 ms follow lock, and 2 s interactive synchronization window. These are product timing choices, not native guarantees.

`terminal_rendering.rs:1230-1270` defines geometry and deadline predicates: within one cell height counts as near-bottom; upward movement means greater Y by more than one pixel while not near-bottom; extent changes require more than one pixel; a deadline equal to now has expired.

`terminal_should_follow_output` (:1361-1368) is OR across near-bottom, follow-lock, interactive-follow and sticky-follow. `should_auto_follow_terminal_output` (:1354-1359) additionally requires an update. Clearing one reason does not negate the others.

## Sync-to-callback execution path

`terminal_session.rs:359-407`, `sync_running_terminals`, samples scroll geometry, follow-lock and interactive-follow. Moving away clears sticky following and clears the stored deadline; being near-bottom enables sticky following. At :558-584 updated/repainted output plus follow eligibility and either forced following, distance, or changed extent schedules the active terminal.

`terminal_interaction.rs:90-166`, `schedule_terminal_follow_scroll`, uses one window-wide pending boolean to coalesce requests. It captures a weak entity and session ID, sleeps in background work, then attempts a window update. The callback:

1. Clears pending.
2. Returns if the currently active terminal ID differs from the captured ID.
3. Re-reads near-bottom, current lock, per-session interactive deadline and sticky state.
4. Requires follow eligibility AND either distance from bottom or changed extent.
5. Scrolls via request_terminal_scroll_to_bottom and notifies.

This is a delayed re-evaluation, not an unconditional scroll command. A failed weak update is ignored; the detached task exposes no explicit cancellation handle in this method.

## Cancellation and ownership limits

- The boolean is window-wide: a pending request for A suppresses scheduling B. If A's callback later sees B, it clears pending and returns; B needs another scheduling opportunity. No retry for B is visible in this function.
- The identity fence rejects A→B but not A→B→A before callback execution. No selection epoch is captured. Whether that return-to-A scroll is desirable needs an application policy; it is not a proven bug.
- Manual-scroll recognition happens during synchronization, not inside the delayed callback. If the callback runs before that recognition, stale sticky state can still authorize following. This is an ordering risk inferred from source, not a reproduced native race.
- The sync pass computes local follow_lock_active before clearing the stored deadline and still uses that cached boolean at :402-406 and :564. This can schedule an extra callback; it does not prove an actual scroll because the callback re-reads the stored deadline.
- Interactive-follow remains an independent OR condition. The examined manual-scroll branch does not clear that deadline. Therefore the source does not establish that every manual upward scroll immediately vetoes all automatic following.

## Direct tests: what they prove

`terminal_rendering.rs:1821-1839`: auto_follow_requires_new_output_and_bottom_position, sticky_follow_keeps_output_pinned_between_bursts, and auto_follow_is_disabled_without_new_output test the boolean predicates. The first test's name is broader than its actual input: it receives should_follow_output, not geometry.

At :1902-1959, active_follow_lock_keeps_output_pinned_between_paints, expired_follow_lock_stops_auto_follow_when_not_at_bottom, interactive_follow_window_stays_active_for_longer_resume_redraws, upward_scroll_during_follow_lock_cancels_follow_mode, and scroll_extent_change_detects_growth_and_ignores_steady_repaints test deadline/movement/extent helpers. The upward-scroll test calls only the movement predicate; it does not execute the state-clearing branch or the scheduled callback.

Crucially, terminal_scheduled_follow_pass_decision is defined inside the cfg(test) module at :1385. Its initial/later/stop retry tests (:1841-1900) do not establish production scheduler retry behavior. A bounded source search found this symbol only in that test module. The production method above has one sleep/update pass, not this retry loop.

All upstream tests were inspected, not executed. No setup or build was run. Active-session switches, manual-scroll timing, weak-window destruction and A→B→A scheduling are not integration-tested by these assertions.

## Heddlework comparison and probe

`src/ui/terminal-view.tsx:97-105` converts scrolling into an ID-addressed row offset. `src/terminal/service.ts:139-145` parses PTY output then calls #anchorDetachedViewport; :289-293 adds new scrollback rows to a nonzero per-session offset. Zero means live tail. `write` (:192-201) returns that session to offset zero. This is emulator-row anchoring, not a window-wide delayed scroll lock.

`tests/terminal-service.test.ts:181-194`, anchors a detached viewport while new output extends scrollback, verifies identical visible rows and offset 1→2 after a new row. The whole module passed 9 tests and 34 assertions.

A direct two-session service probe additionally passed: output anchors inactive A without changing B's offset; selection back to A preserves its offset; input resets A to tail; the first small post-input response publishes immediately; a subsequent ordinary response queues a frame; closing A discards that queued frame and detaches its data listener. The first probe incorrectly counted the immediate frame as post-close output. The corrected probe explicitly asserted immediate delivery, reset the observation window, then queued the next response. No application fix was made.

`service.ts:235-256` removes session cleanup callbacks, kills the process and deletes dirty-frame IDs; :310-322 skips vanished sessions during frame publication. The probe uses an injected backend, not a PTY/native view. Scrollback-cap eviction and native input ordering remain outside its proof.

## Disposition

**ADAPT.** Preserve callback-time identity/liveness revalidation and the distinction between eligibility and actual scroll work when adding delayed UI effects. Do not transplant Arbor's window-wide follow state into Heddlework's per-session row model. A strict manual-scroll veto would need an explicit user-intent/selection generation and integration tests rather than reliance on OR predicates.

## Retrieval and next uncertainty

Existing full graph: heddlework-inspo-arbor. This pass used direct bounded source searches; no graph freshness/completeness claim. Load this capsule only for following/scheduling questions. The next distinct local uncertainty is detached viewport behavior when bounded scrollback evicts old rows; the growth-only anchoring test does not answer it.
