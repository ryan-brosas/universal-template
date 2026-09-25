---
name: judged-agent-pipelines
description: "Use when building, tuning or reviewing a long-running agent whose decisions come from typed judges (Jev, classifiers, scoring calls) rather than from generated text: supervising loops, acquisition through a browser or API, gating, human review queues, and the calibration work that makes the judge trustworthy. Covers calibrating question wording against known samples, moving hard rules into code, critic-driven repair, threshold sourcing, resilience proofs and platform-compliance boundaries."
---

# Judged agent pipelines

A judged pipeline separates four responsibilities. Keep them separate or the agent will look clever and be untrustworthy.

| layer | owns | must not do |
| --- | --- | --- |
| acquisition | paging, pacing, parsing, dedupe | decide anything |
| judges | semantic calls on bounded inputs | enforce hard rules |
| code | thresholds, transforms, gates, budgets | ask a model for certainty |
| human queue | release of anything external | be bypassed by the agent |

The output of a cycle is a decision plus its evidence, never a side effect nobody approved.

## Calibrate before you trust

A judge question is a measuring instrument. Test it against samples whose correct verdict you already know, and discard any question that does not separate them.

1. Write four to six samples: one clearly acceptable, and one each for the failure you care about (promotional, stilted, speculative, off-target).
2. Ask the candidate questions about all samples in one call. Judgments are independent and share state, so batching is free.
3. Compare. If a bad sample scores better than a good one, the question is broken, not the sample.

A real example. The question "is the draft plain, conversational, non-templated and free of em dashes" scored a marketing draft 0.66 and a stilted draft 0.79 against a clean draft at 0.68. Useless. Splitting it into narrow defect questions fixed it, on the same samples:

| sample | assistant voice | asks back | asserts internals | concrete |
| --- | --- | --- | --- | --- |
| clean and check shaped | 0.03 | 0.07 | 0.06 | 0.92 |
| promotional | 0.93 | 0.16 | 0.24 | 0.14 |
| stilted and vague | 0.99 | 0.62 | 0.07 | 0.11 |
| asserts vendor internals | 0.02 | 0.02 | 0.94 | 0.15 |

Rules that fell out of that work:

- One defect per question. Compound judgments with a negative qualifier measure nothing.
- Ask about a named defect ("does it open with a caveat instead of a claim"), not an aesthetic ("is it good").
- Word the question around the exact failure you mean. "Does it assert anything unverifiable about a third party" scored a clean check-shaped reply 0.15 and pushed every specific answer toward failure; "does it assert as fact how another company's product behaves internally" scored internals 0.94 and checks 0.06.
- Keep a deterministic counterpart in code for anything countable (length, punctuation, links, bullets). Judgments are for meaning.

## Move hard rules into code

A prompt is a request, not a control. In a live run the model ignored an explicit "never name the employer" instruction and opened with the employer clause anyway. The fix was a transform in code that removes the forbidden clause and any sentence naming the company before review, with the judge as the second check. Prompt rules bias behaviour, code rules guarantee it.

## Gate what should not be answered

Before spending generation on an input, classify whether it is answerable by this agent at all. A single choice question over checks, firsthand, insider and none is enough. Only one option proceeds. This is what stops an agent from producing confident speculation about topics it can only guess at, and it saves the generation cost.

## Let the critic drive one repair

When a draft fails review, turn the failing scores into the repair instruction, regenerate once, re-review, and keep whichever version scored better. Cap it at one pass with a bounded budget, otherwise the loop burns tokens arguing with itself. Log both versions so a human can see which complaints were actionable.

## Thresholds come from measurements

Set gate values against the distribution you measured, and record why. Cite the calibration numbers in the code or the doc next to the threshold. A threshold that exists to make one sample pass is fitting, not tuning.

## Prove resilience, do not assume it

Run these before calling a supervised agent done:

- Kill its dependency mid-cycle (browser, socket, API). One cycle should fail loudly, the next should recover on a fresh session.
- Restart the service mid-cycle. It must exit promptly, resume from persisted state, and reprocess nothing. Verify with a duplicate count on the state table.
- Confirm one writer only. Two workers on one queue double-process and corrupt pacing.
- Confirm the kill switch stops it at a cycle boundary and stays stopped.
- Confirm no external write path exists unless it was explicitly built and approved.

## Recording decisions

Persist every judgment with its inputs, model, latency and token usage, plus an action log of gates, skips, repairs and blocked releases. The log is what lets you answer "why did it do that" a week later, and it is the only honest basis for cost claims.

## Boundaries

- Never automate a human account where the platform forbids it. Automation belongs to a bot identity the platform provides, or to a human who publishes what the agent prepared.
- Prefer identity-based disclosure (a verified role or a named account) over a disclosure clause in every message, and check the destination's rules before assuming either. Block any message that names your product without disclosure.
- An agent that reports "no match" is working. An agent that always finds something is guessing.

## Deliverable checklist

- Acquisition, judges, code gates and human queue are separate, and each is testable alone.
- Every judge question survives the sample battery, and the battery lives next to the prompt.
- Hard rules are enforced in code, with the judge verifying as a second layer.
- Unanswerable inputs are classified out before generation.
- Thresholds cite a measured distribution.
- Resilience proofs exist for dependency loss, restart, duplicate processing, kill switch.
- No unapproved external write path.
