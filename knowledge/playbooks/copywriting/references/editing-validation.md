# Editing, Audits, and Validation

Load this capsule for diagnosis, rewrites, final review, or experiments. It
owns the why-is-this-weak pass and the proof behind “does it work”. Channel
capsules own the expression; this capsule owns the judgment.

## Diagnose before rewriting

Rewrite without diagnosis is decoration. Name the exact failure first:
segment + stage + behavior + evidence.

- Weak: “This page needs to convert better.”
- Exact: “Paid problem-aware visitors reach the pricing section but do not pick
  a plan; interviews show uncertainty about fit.”

Trace the failure one or two steps upstream. A drop at the CTA may be a promise
broken in the opening. A drop in plan selection may be a pricing-card clarity
defect. Read the copy the way the segment does, in order, and find the first
place the argument's promise stops being delivered.

Diagnostic order:

1. **Goal and match:** Is there one intended action? Does the opening continue
   the source promise and fit awareness?
2. **Hierarchy:** does each section answer a reader question and advance one
   belief? Remove repetition before evidence.
3. **Clarity:** could a reader say what this is, who it is for, and why it
   matters?
4. **Specificity:** replace abstractions with situations, mechanisms, limits,
   and outcomes.
5. **Relevance:** is every unit attached to the chosen reader's decision?
6. **Differentiation:** remove what a credible competitor can claim unless
   mechanism or proof makes it distinct.
7. **Proof:** does claim-specific evidence sit beside each material assertion?
8. **Objections and friction:** are material concerns answered where they
   arise, and are interface defects named, not hidden?
9. **CTA:** readiness, findability, honest commitment, next-state value.
10. **Tone:** does the voice fit the channel without out-shouting the content?

Use this critique shape, in order:

> Observation → why it changes the reader's decision → the editing principle
> that fixes it → concrete rewrite of the unit.

A “punchier” comment is a preference, not a diagnosis, until you name the
belief the current phrasing fails to establish.

## Claim ledger

Keep a user-visible claim table:

| Claim | Type | Evidence/source | Scope or qualifier | Status |
|---|---|---|---|---|
| outcome | performance | measured result | segment and period | approved/placeholder |
| capability | product | docs/demo | plan or limit | approved/placeholder |
| social proof | customer | approved source | exact attribution | approved/placeholder |
| urgency | offer | real policy/date | timezone/stock rule | approved/placeholder |

Then:

- Delete or qualify unsupported claims.
- Do not turn “two customers reported” into “customers achieve”.
- Do not generalize one testimonial into the typical result.
- Mark everything not yet verified as `[PLACEHOLDER: evidence needed]`.

## Editing passes

Run passes separately so fluency cannot hide logic errors:

1. Evidence and factual accuracy (claims vs. proof)
2. Argument and section jobs (does each part advance the decision?)
3. Clarity and concrete language (nouns, verbs, specifics)
4. Compression and rhythm (cut repetitions, tighten)
5. Voice consistency and channel fit
6. CTA, links, labels, and the end-to-end action path

Read aloud only after the reasoning passes. If your attention slides on a
sentence, that is where a reader will drop.

## The edit mindset

Editing is not the same as rewriting. Preserve the writer's argument; change
only what does not serve it. If the base copy has a real claim and honest
structure, editing adds specificity and clarity rather than replacing the
voice. Rewriting wholesale loses evidence found in existing phrasing. When you
do rewrite, take the claim and its proof with you.

## Validation ladder

Choose the cheapest method that answers the current uncertainty:

1. Stakeholder claim review (does everyone agree the claim is honest?)
2. Five-second test: what is it, who is it for, why care?
3. Message test or preference interview; probe why, not just which
4. Usability test of the page, form, onboarding, or checkout
5. Customer interview or on-page survey for unresolved motivation
6. Controlled experiment when traffic, instrumentation, and stakes justify it

Escalate only when the cheapest answer is not enough. A question about headline
recognition does not justify a live A/B split; a question about revenue impact
does not resolve from a five-second test.

## Experiments that teach

An experiment that only reports “winner” taught nothing. Make the lesson
explicit.

Write an experiment as:

> For **[segment / audience state]**, **[message contrast]** should change
> **[primary behavior]** because **[belief / motivation / objection]**, without
> reducing **[downstream outcomes]**.

The “because” clause is the belief under test, not just the phrasing. Local
metrics (CTR) validate the change's influence; downstream metrics (purchase)
are the guardrail.

Do:

- Test one primary change per flight when learning needs attribution.
- For strategic questions, test a bundle and report the bundle's effect, not
  per-element attribution.
- Record sample, duration, assignment, metric changes, and downstream impact.
- Treat a flat result as a result when the contrast was real: state it, then
  form the next question.
- Report a winning bundle as a bundle result; do not infer which ingredient
  caused it.

Do not:

- Extrapolate from one winner to a universal rule.
- Declare “it works” from CTR alone without a link to the final action.
- Extend a test indefinitely chasing significance; reset the design for
  additional exposure instead.

## Review triggers

Re-audit copy when:

- the offer, pricing, integration, or capacity changed;
- new customer evidence contradicts a claim or language;
- baseline performance shifted beyond normal noise;
- the channel, source, or audience changed;
- regulatory or legal constraints changed.

## Delivery: the audit report

Write the audit as judgment, not a notepad: state the failure chain, what you
changed, and why. Deliver:

- updated copy in order, with placeholders for anything unverifiable;
- the exact diagnoses you applied (each a line);
- the claim ledger;
- what you measured or will measure, and when a second pass is due.

## Verifying your own work

- Read the copy aloud cold; cut anything that earns no place.
- Use the “I want to” test on every CTA.
- Recheck each claim against its source.
- State placeholders explicitly: what is verified, what is not.
- Run the diagnostic order one final pass before calling it done.

## Stopping rules

| Stage | Stop when | If not satisfied |
|---|---|---|
| Diagnosis | one paragraph naming segment, stage, behavior, evidence | do not draft yet |
| Claim check | every substantive claim has a source or placeholder | hold the copy |
| First edit pass | claims and logic are sound | stay in this pass until they are |
| Fine pass | vague words, long sentences, and repetition resolved | ask “what does the reader need to believe next” before adding more |
| Validation | smallest method answers the question | escalate the ladder |

## Acceptance checklist

- Important claims carry real evidence or a named placeholder.
- No statistic, testimonial, capability, guarantee, urgency, or case is
  invented.
- No complaint hides behind bulky sentences.
- The CTA names an honest next step; the price is not hidden.
- The conclusion of any test matches the metric measured.
- Design or product defects are reported separately from copy problems.
