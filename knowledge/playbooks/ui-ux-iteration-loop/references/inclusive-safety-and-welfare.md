# Inclusive Design, Safety, and Longitudinal Welfare

Accessibility is not a final scan, and an average improvement can conceal concentrated harm. Apply these gates while framing, designing, implementing, and evaluating—especially for health, finance, identity, privacy, employment, education, children, subscriptions, destructive actions, or consequential automation.

## Capability and context matrix

Test requirements rather than inventing a mythical “average user.” Select relevant rows from the actual task and audience.

| Dimension | Stress condition | Evidence to inspect |
|---|---|---|
| Vision | low vision, color-vision difference, zoom, glare, dark mode | reflow, contrast, noncolor meaning, text alternatives, magnification path |
| Hearing | audio unavailable or imperceptible | captions/transcripts, visual equivalents, notification persistence |
| Motor | tremor, limited reach, switch/voice/keyboard use, one-handed mobile | target tolerance, order, shortcuts, accidental activation, timeout control |
| Cognitive/learning | low literacy, dyslexia, memory/attention limits, unfamiliar domain | plain language, recognition, chunking, error recovery, teach-back |
| Speech/language | speech input, second language, localization, right-to-left text | labels, parsing, expansion, reading/order, locale formats |
| Temporary/situational | injury, stress, interruption, bright/noisy setting, slow network | resumability, persistence, status, reduced demand, offline/partial failure |
| Experience | novice, infrequent, expert, administrator | discoverability, explanations, efficiency, safe shortcuts, role clarity |
| Technology | old/slow device, narrow viewport, assistive stack, reduced motion | progressive enhancement, latency, reflow, semantics, preference support |

Do not claim coverage because one automated tool passed. Name the standards target, tools, manual paths, assistive technology, browsers/devices, content, and states actually tested.

## Exclusion audit

Before evaluating a treatment, ask:

1. Who cannot enter, perceive, understand, operate, recover, or safely decline this flow?
2. Which people disappear from analytics because they never start, block tracking, use another channel, contact support, or abandon before instrumentation?
3. Does the improvement shift work or risk to a smaller group, support staff, caregivers, or future users?
4. Are identity, language, disability, age, geography, income, device, role, or trust differences mechanistically relevant?
5. Can an alternative path provide equivalent outcome without segregating users into a degraded experience?

Segment only where a prior mechanism predicts a difference. Protect privacy and avoid collecting sensitive attributes merely to decorate a dashboard.

## Harm and reversibility model

Rate each plausible failure on:

- **Severity:** inconvenience → blocked work → loss, exposure, discrimination, injury, or legal/financial consequence.
- **Likelihood and exposure:** frequency, duration, affected population, and repeated accumulation.
- **Detectability:** whether the user or operator notices before harm occurs.
- **Reversibility:** undo, correction window, restoration, appeal, export, human review, and cost of recovery.
- **Distribution:** who receives benefit and who bears error, labor, delay, or risk.

High-severity, hard-to-detect, irreversible failures require prevention, explicit status, conservative defaults, human escalation where appropriate, and stronger pre-release evidence. Never average away a critical failure.

## Material-choice comprehension gate

For consent, pricing, renewal, privacy, destructive actions, and consequential AI output, verify that a representative user can explain before committing:

- what will happen now and later;
- material cost, duration, uncertainty, data use, and affected parties;
- whether a default or recommendation is active and whose interest it serves;
- how to decline, correct, cancel, appeal, recover, or reach a human;
- what the system does not know or guarantee.

A clicked checkbox is not evidence of comprehension or freely given choice. Decline must not impose disproportionate friction, and cancellation should not be materially harder than enrollment.

## Longitudinal guardrails

Immediate task success can create delayed harm. Choose guardrails on the timescale implied by the mechanism:

- **Hours/days:** errors, rework, support contacts, reversals, refund requests, notification disablement.
- **Weeks:** retention with intent, cancellation success, complaint themes, trust, dependency, unequal outcomes.
- **Months:** accumulated fees, lock-in, wellbeing, learning effects, accessibility debt, operator workload, and behavior adaptation.

Assign an owner and review date. If delayed evidence cannot be observed before release, stage exposure, preserve rollback, and state the residual risk.

## Safety verdict

Do not advance when any critical group is blocked or exposed to material unrecoverable harm; the choice cannot be understood or declined; evidence excludes the population bearing risk; or a metric gain depends on deception, compulsion, hidden cost, inaccessible recovery, or fabricated confidence.
