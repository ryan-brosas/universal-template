---
name: inspo-qualify
description: "Use when an active project needs external GitHub prior art: discover or assess one candidate, then clone and full-index it in Codebase Memory only after explicit approval."
invocation: entry
---

# Inspiration Qualification

## Core Principle

`/inspo` starts with a real question in the active project, not a repository
quota. It finds or accepts one external implementation that can close that
gap. Codebase Memory maps the approved external source; direct source and tests
prove claims. The process is manual, evidence-led, and stops when the question
is answered.

## When to Use / NOT

- **Use when:** the active project needs external prior art for a named seam;
  the user supplies a GitHub candidate; or the user asks to go deeper on an
  already qualified inspiration repository.
- **NOT when:** ordinary project orientation answers the question; an existing
  inspiration project already covers it; the candidate is an active owned
  project; or there is no project need to investigate.

## Qualify one candidate

1. Inspect the active project's relevant source and tests. State the named
   question. If the user gives only `/inspo`, derive the most useful unresolved
   question from that evidence instead of starting a questionnaire.
2. Check existing Codebase Memory projects and Git remote identity. Reuse an
   equivalent source when it closes the question. Otherwise search GitHub
   manually or assess the nominated URL. Inspect its source tree, direct tests,
   pin, license, maintenance signals, and transferable boundary.
3. Stop discovery for a missing current-project question, duplicate inspiration
   identity, active owned project, or missing recorded OSI-recognized license
   (or `NO-LICENSE` pattern-only obligation). Explicit approval is the separate
   hard gate before any clone or index action.
4. Before mutable work, present one in-chat record and obtain approval:

   ```text
   Project need: <question and active-project paths>
   Candidate: <owner/repo @ exact commit>
   Evidence: <source, tests, license, maintenance, expected value>
   Counter-evidence: <gaps, transfer and index-cost risk>
   Decision: QUALIFY | DEFER | REJECT: <reasoned confidence>
   ```

   Approval applies to this exact candidate and pin. Popularity, test count,
   repository size, and clone count are evidence only, never thresholds.
5. After approval, clone the resolved commit under
   `/mnt/hdd/utopia/inspo/<repository-name>` without overwriting another
   checkout. Cloning supplies source evidence; do not install dependencies,
   run a setup script, or run a bulk miner to learn it. Read direct test source;
   run a test only when it already works without setup, otherwise report the
   caveat.
6. Follow `codebase-memory` to request `mode: "full"`, then verify ready status,
   coverage for cited source/test paths, and one bounded graph probe. Record the
   root, pin, license, coverage caveat, and graph result in the chat. The graph
   is a retrieval map, not proof.

## Go deeper

For repeat in-place revision of an existing Foundation Pack source, use a bounded `/learn` evidence pass on one named seam; this skill keeps ownership of external-source qualification and approval. For ordinary `go deeper`, resume the approved repository from current source, project-scoped session evidence, and any qualified work record. Choose one high-value unresolved seam,
not a broad repository sweep. Trace its entry points, data/control flow,
invariants, failure boundaries, configuration, and direct tests. Return the
verified model, citations, counter-evidence, and next candidate seam.

When the user explicitly starts a long-running or handoff-heavy campaign,
create one compact `docs/plans/inspo-learning-<repo>.md` coordinator before the
clone/index action. It records the exact pin and license, named questions,
non-goals, completion criteria, freshness policy, verified passes,
counter-evidence, and next target. One-off qualification stays in chat.

## Promotion

A completed pass can answer the active-project question without creating a
repository artifact. Classify reusable outcomes through `leverage-capture`.
A foundation needs cited, reusable source-grounded architecture and explicit
user promotion. A Skill needs a repeated real procedure, not facts from one
repository. Never generate either automatically.

## Red Flags

- Search, clone, index, or promotion without a current-project question and
  explicit approval.
- Dependency installation, generated-analysis scripts, or bulk repository
  mining used as a shortcut.
- Codebase Memory output treated as behavioral truth.
- A long-run record for a one-off question, or a source dump inside one.
- Continuing to search after the evidence gap is closed.

## Verification

Pressure-check the procedure: a duplicate is reused; an active owned project
is rejected; an unapproved candidate stops before clone/index; an unrunnable
test is a caveat rather than an install request; and a first-pass repository
can become neither a foundation nor a Skill automatically. For an admitted
source, confirm the pin, license, full-index request, ready status, cited-path
coverage, graph probe, and exact source/test evidence.

## References

- `../codebase-memory/SKILL.md`, index lifecycle and source-of-truth limits
- `../reference-driven-development/SKILL.md`, prior-art selection and direct-test discipline
- `../leverage-capture/SKILL.md`, earned promotion classification
