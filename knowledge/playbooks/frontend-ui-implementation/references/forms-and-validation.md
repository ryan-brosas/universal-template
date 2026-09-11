# Forms and Validation Implementation

## Structure and spacing

- Use a persistent `<label>` for every control. Placeholder text is an example or format hint, never the only label.
- Build one clear top-to-bottom sequence. Multiple visual columns are acceptable for one compound value (for example day/month/year) only when DOM, reading, error, and tab order remain coherent.
- Make within-field spacing smaller than between-field spacing so label, hint, control, and error form one perceptual group. Use shared stack tokens rather than arbitrary margins.
- Size fields to expected content when practical, but let them reflow on narrow screens. Width communicates expectation; `maxlength` is a data rule, not a visual fix.
- Mark required or optional status per field consistently. Do not depend on instructions users must remember from the top of the form.

## Inputs and choices

- Use the semantic input type, `inputmode`, `autocomplete`, and name expected by browsers and password managers. Test mobile keyboards and autofill.
- Use radios or exposed choices for a small, meaningful set; searchable combobox/listbox patterns for large familiar sets; direct entry when typing is easier. The PDF’s **5–7 option** suggestion is a heuristic, not a cutoff.
- Preserve native file-input semantics when custom styling adds preview, size/type validation, progress, cancel, error, and retry. The control must remain keyboard and screen-reader operable.
- Autofocus only when context is stable and immediate typing is clearly intended. Do not steal focus, skip content, or summon a mobile keyboard unexpectedly.
- Keep a password reveal control in its own stable hit area so it does not overlap text or interfere with password managers. Preserve cursor, value, accessible name, and pressed state.

## Guidance and validation

- Put task-critical hints and password rules visibly near the field before submission. Tooltips can supplement, not own, required instructions.
- Prevent errors with constraints, examples, sensible defaults, correct formats, and unavailable-option handling. Do not silently alter user data.
- Validate at a timing that helps correction without punishing typing. Positive validation is useful for difficult or consequential input, not every ordinary field.
- Place specific actionable errors with the responsible field, connect them programmatically, expose an error summary when useful, and focus or scroll to the first invalid control without disorienting users.
- Preserve entered values after errors and across recoverable handoffs. Prefill known email or repeated process data when accurate, expected, editable, privacy-safe, and allowed by the security contract.
- Progressive disclosure must keep advanced/rare controls discoverable, preserve expansion and focus state, and never hide prerequisites, active values, or consequences.
- Long checkbox/filter sets may collapse only when the trigger exposes the applied count/state and users can inspect, clear, and operate every choice by keyboard.
- Multi-step forms must earn the extra navigation: reduce fields first, group by user task, show meaningful progress, preserve state, support backtracking, and recover after interruption or session expiry.

## Submission and verification codes

- Prevent accidental duplicate submission while maintaining perceivable state. Server-side idempotency owns financial or irreversible duplicate safety.
- Auto-submit a complete verification code only when completion is unambiguous, paste/autofill work, errors are recoverable, repeated attempts are safe, and status is announced. Otherwise retain an explicit submit action.
- Keep verification purposes clear without deliberately exposing authentication codes in lock-screen or mirrored-device previews. For app-controlled push notifications, use redacted previews and reveal codes only after unlock. Prefer OS-controlled OTP autofill; SMS senders cannot guarantee how a recipient's messaging app displays previews, so do not claim wording alone makes delivery private.

## State contract

Test default, focus-visible, filled, autofilled, valid, invalid, disabled-with-reason, read-only, loading, timeout, offline, server rejection, success, back navigation, retry, and expired session. Test keyboard, touch, speech input, password managers, zoom, RTL, long labels/errors, and screen-reader announcements.

## Verification

Submit empty, malformed, boundary, duplicate, and valid values. Confirm labels and descriptions survive entry; tab and reading order match; focus lands predictably after validation; values survive recoverable failure; autocomplete/input modes work; custom choices expose name/role/value; and loading/retry cannot duplicate the operation.
