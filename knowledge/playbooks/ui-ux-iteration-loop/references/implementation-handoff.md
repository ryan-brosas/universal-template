# Design-to-Implementation Handoff Contract

A UX hypothesis is not implemented when only the ideal screenshot matches. Translate the intended behavior into an inspectable contract without prescribing incidental code structure.

## Handoff packet

```text
Iteration/treatment ID (links to canonical governance record):
Task and affected users/context:
Evidence status and earliest break:
Mechanism + competing explanation:
Treatment and predicted behavior:
Non-goals / variables held constant:
Primary outcome, threshold, guardrails, rollback:
Flow, service/channel seams, and ownership boundaries (channels/actors, shared state, confirmation, escalation, recovery owner, equivalent outcome or accepted residual risk):
State matrix:
Content and data extremes:
Interaction and semantic contract:
Responsive/adaptive rules:
Analytics/research instrumentation:
Design-system mapping and intentional exceptions:
Privacy/security/safety constraints:
Acceptance evidence and artifacts:
Open risks, owner, review date:
```

## State model

For every user action and system boundary, define only applicable states:

- initial/default, hover where meaningful, focus, active/pressed, selected;
- disabled **with a perceivable reason** when users need to understand availability;
- loading, queued, offline, stale, partial, empty, permission denied;
- validation warning/error, system error, timeout, retry, cancellation;
- success, undo, resume, duplicate/idempotent submission, expired session;
- destructive confirmation when irreversibility warrants it;
- long/localized content, zoom/reflow, narrow/wide viewport, reduced motion, high contrast, and assistive semantics.

Record transition trigger, visible status, preserved data, focus destination, announcement, available actions, retry behavior, ownership, and terminal outcome. “Handle errors” is not a state contract.

## Interaction and semantics

Specify behavior independently of pointer-only visuals:

- semantic role, accessible name, description, state, and relationship;
- keyboard order and commands, focus entry/return, escape/cancel, and no focus loss after updates;
- touch target and gesture alternative; no gesture, hover, drag, color, sound, or motion as the only path;
- validation timing, error association, announcement, and preserved input;
- confirmation/undo matched to severity and reversibility;
- loading ownership, layout stability, concurrency, repeat activation, and interruption/resumption;
- reduced-motion behavior and timing controls.

Prefer native platform semantics. A custom control must earn its complexity and reproduce expected interaction across relevant modes.

## Content and data contract

Use real content shape, not lorem ipsum. Include:

- shortest, typical, longest, empty, malformed, duplicate, and adversarial values;
- localization expansion, right-to-left layout, locale dates/numbers/currency, pluralization, and names outside Western assumptions;
- unknown, delayed, stale, conflicting, permission-filtered, and partially loaded data;
- truthful price, renewal, privacy, sponsorship, recommendation, and automation-limit copy;
- truncation behavior plus an accessible way to obtain the full value where needed.

Never solve overflow by silently deleting task-critical information.

## Responsive and adaptive contract

For each meaningful range, specify what reflows, wraps, stacks, scrolls, condenses, or moves—and what must remain visible for the task. Preserve reading order, focus order, comparisons, current state, and action priority. Device width alone is not context: consider input mode, zoom, safe areas, virtual keyboards, orientation, network, and platform conventions.

## Instrumentation contract

Events must represent observable user and system behavior, not guessed intent. Define event name, trigger, properties, denominator, exposure, success/failure, version, privacy limit, and owner. Test events with the flow. Instrument recovery and negative outcomes—not only impressions and conversion. A changed event schema invalidates historical comparison until reconciled.

## Acceptance layers

1. **Contract:** intended transitions, content, semantics, and ownership are implemented.
2. **Deterministic:** functional, state, accessibility, visual-regression, and instrumentation checks pass where appropriate.
3. **Rendered:** representative viewports, themes, zoom, content extremes, and states are inspected against before/after evidence.
4. **Behavioral:** the treatment receives the method chosen in `experiment-and-evidence.md` without overstating confidence.
5. **Operational:** rollout, observability, support/recovery path, delayed guardrails, and rollback are owned.

## Drift control

When implementation constraints force a behavior change, update the handoff and hypothesis before silently substituting a different treatment. Record deliberate design-system exceptions with rationale and a removal/review condition. Acceptance criteria protect user-visible invariants, not arbitrary pixel or component structure unless exact fidelity is the stated goal.
