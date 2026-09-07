# How is a control key delivered once when keydown and IME text both fire?

Source: [penso/arbor at d8d82b7eec6cba3682374875d8f13407c7181ef0](https://github.com/penso/arbor/tree/d8d82b7eec6cba3682374875d8f13407c7181ef0), MIT. Paths below are source-relative.

## Entry, data and control flow

`crates/arbor-gui/src/terminal_interaction.rs:622-747`, `ArborWindow::handle_terminal_key_down`, excludes modal/nonterminal consumers, resolves the active terminal, handles platform copy/paste, then derives terminal bytes and a possible fallback control byte. No bytes means store `ConvertControlByte` and allow IME propagation. Already emitted bytes equal to the fallback byte mean store `SuppressControlByte`; unrelated byte sequences do not arm suppression. A write error becomes a visible notice; successful writes notify the terminal. Keydown propagation stops for encoded input.

`terminal_interaction.rs:17-49`, `resolve_terminal_text_input_followup`, matches text against the stored byte and returns `Convert(u8)`, `Suppress`, or no match. The window method consumes pending state with `.take()` before matching: unrelated text cannot leave a stale suppression token armed.

`crates/arbor-gui/src/rendering.rs:117-143`, `replace_text_in_range` terminal branch, resolves the active session and consumes that state: Convert writes one byte; Suppress writes nothing; unmatched text falls through to ordinary bytes and input tracking. Failed writes surface a notice and return. This is two-channel deduplication, not blanket rejection of caret text.

## Invariants and failure boundaries

- Suppression depends on actual emitted bytes, not merely Ctrl.
- The token is window-owned, not session-keyed. Switching sessions between keydown and text is not proven safe. This is distinct from the delayed-scroll fence.
- The token is installed before writing; failed keydown writes still leave suppression armed. This is not a retry guarantee.
- `.take()` is single-consumption cleanup, not a timeout. Modal/focus transitions need native integration tests.

## Direct tests and limits

`terminal_interaction.rs:768-800`: `convert_followup_returns_control_byte_for_matching_caret_text` establishes `^A` → 0x01; `suppress_followup_drops_matching_control_text` establishes `^Z` → Suppress; `mismatched_text_does_not_match_pending_followup` rejects `a` for Ctrl-A. These test the pure resolver, not `.take()`, dispatch order, session switching or write failures. Read directly, not executed: no existing upstream target and no setup performed.

## Local comparison

Heddlework `src/ui/terminal-view.tsx:71-96` encodes GPUIX key events and calls session-ID-addressed `service.write`; `src/terminal/service.ts:192-201` drops absent/exited sessions and returns input to the live tail. It has no Arbor two-channel token at this boundary. `tests/terminal-keys.test.ts:7-17` verifies printable/control/navigation encoding including `ctrl-c` and control-byte keyChar. Together with the service module, 12 tests passed, 48 assertions. This does not establish native duplicate-event behavior.

**Disposition: ADAPT.** Preserve one-shot byte-matched deduplication only if a live GPUIX reproduction establishes dual delivery. Adapt at the native/text bridge with receiving session/focus-generation ownership; do not introduce a second input owner.

## Retrieval and coverage

Search `control text followup` in this foundation. Existing full graph project `heddlework-inspo-arbor`, source search `resolve_terminal_text_input_followup`, then read the ranges above. This pass used direct source, not graph execution; prior index-health metadata is not fresh verification. Directly re-read `terminal_interaction.rs:1-170,622-803`, `rendering.rs:102-174`, the local input/service ranges, and both local test modules. Re-executed the two local modules: 12 pass, 0 fail, 48 assertions. Upstream tests were inspected, not executed; no setup/build was attempted. Native event ordering remains unverified.

### Decisive source anchors

The single-consumption boundary is `let pending = self.pending_terminal_text_input_fallback.take()?;` at `terminal_interaction.rs:48`; the byte-match gate is `.filter(|control_byte| input.as_slice() == [*control_byte])` at :731. In contrast, `schedule_terminal_follow_scroll` at :89-166 weakly references the window, clears its pending flag on update, and rejects a changed active session at :116-118 before scrolling. That delayed-scroll fence does not make the window-owned input token session-safe. Its native scheduling path was read, not tested in this pass.
