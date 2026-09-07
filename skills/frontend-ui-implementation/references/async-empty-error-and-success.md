# Async, Empty, Error, and Success States

## Stable loading behavior

- Reserve final geometry when practical. Skeletons can preserve large-content layout; compact spinners suit bounded controls. Skeleton shape must approximate the real content and respect reduced motion.
- Keep a button’s width and label context stable while submitting. Prefer a reserved label box or minimum inline size; hiding text with transparency must not expose duplicate accessible content.
- Attach progress to the region or action that is changing. A page-wide overlay must cover and center within the actual viewport, manage focus only when interaction is truly blocked, and never hide an offscreen spinner.
- Avoid loader flicker for imperceptibly short waits, but never use the PDF’s example delays (**~0.2s load, <0.5s before loader**) as universal timing. Use measured latency and platform feedback expectations. Delayed indicators still need immediate pressed/disabled acknowledgement when repeat activation is dangerous.
- For long work, show truthful stages, elapsed/progress information when known, cancellation/background behavior, and recovery. Never rotate fake “almost done” messages when progress is unknown.

## Empty states

Distinguish first use, filtered zero results, permission-limited, cleared content, failed loading, and true absence. Explain why the space is empty, preserve surrounding context, and offer the relevant first or recovery action. Do not turn blocked access into cheerful onboarding.

## Errors and recovery

- Explain what happened in user language, what was preserved, and what can happen next. Keep technical detail in diagnostics, not the primary message.
- Preserve user work. Provide retry, edit, undo, alternate route, support/escalation, or safe exit as applicable.
- Associate field errors with controls; use an error summary for multi-error forms when useful; announce asynchronous errors and return focus predictably.
- Handle timeout, offline, stale data, partial success, permission loss, expired session, cancellation, and duplicate response—not only generic failure.
- 404 and unavailable routes retain navigation and provide useful destinations/search rather than a dead end.

## Success and transient feedback

- Success must be perceivable and durable enough to answer “what happened?” and “what next?” Do not rely only on a disappearing toast.
- Keep notifications short; provide a durable destination for details. Queue or consolidate simultaneous notices, prioritize safety-critical information, and support pause/dismiss/history where required.
- For deletion or mutation, expose undo for the real reversibility window and make its result idempotent. High-risk irreversible actions still need prevention before execution.
- Preserve status across route changes when the operation continues elsewhere. Email, push, background jobs, and in-app state must not contradict one another.

## State-transition checklist

For each transition record trigger, pending signal, disabled/repeat behavior, focus destination, live announcement, preserved state, cancel/retry, stale-response handling, owner, terminal success, and rollback. Abort or ignore out-of-order responses so old requests cannot overwrite current UI.

## Verification

Throttle network and CPU; force empty, partial, offline, timeout, stale, permission, server, cancellation, retry, duplicate, and success paths. Check cumulative layout shift or equivalent visual stability, repeat activation, idempotency, focus, announcements, reduced motion, refresh/resume, and cross-channel consistency.
