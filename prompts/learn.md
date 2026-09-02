# Learn an approved source

Use this command to investigate source and tests, not to manufacture knowledge.
Codebase Memory is a structural map. Direct source and direct tests decide what
is true. Keep findings compact, cited, and useful for the active project.

## Modes

- `/learn <source or question>`: run one manual evidence pass on an already
  approved source.
- `/learn --auto foundation-pack`: run a bounded, sequential revision campaign
  over one eligible Foundation Pack source group at a time.
- `/learn --auto foundation-pack continue`: resume the campaign. Read the
  coordinator deterministically: consider `docs/plans/inspo-learning-*.md`
  in ascending `(repo pin)` order and take the first record whose group has
  no COMPLETE or SATURED terminal disposition recorded. A record that already
  records COMPLETE or SATURED for its pinned seams is closed: do not re-enter
  or re-approve it. Use that record's `Next target` first, finish that
  seam, then chain on to the next eligible source group.
- `/learn --auto foundation-pack --loops N` (alias `--loop N`): process at
  most N source groups in this run (unbounded means "until a real stop", not
  "skip checks"). After each group reaches a terminal state, choose the next
  eligible group by claim risk, reusable value, and source/test quality.
  `--auto` without a `foundation-pack` target is a usage error: state the
  target explicitly and stop.
- `--reflect`: after the run, invoke the read-only `/reflect-memory` pass
  over project memory before recommending any new campaign batch.

`--auto` authorizes the in-session selection and repeat of evidence passes. It
does not authorize unattended work, GitHub discovery, cloning, indexing,
dependency installation, setup scripts, bulk mining, or promotion into a new
foundation or Skill. Route any missing source to `/inspo` and stop. A very
large `--loops N` does not change these boundaries; it only relaxes the
between-group count limit. At each named stop, pause and report: budget used,
groups terminal, groups blocked, next seam, and what a fresh `continue`
resumes.

## Preflight

Read the current project's instructions, relevant Foundation Pack leaves, their
portable source identity and exact pin, and the existing migration/work record.
For `--auto foundation-pack`, group leaves by upstream identity and exact pin.
Choose one source group only when it has:

- a Foundation Pack claim with a named evidence gap;
- readable source at the recorded exact pin;
- a recorded license or explicit `NO-LICENSE` limitation;
- a ready full-mode Codebase Memory index; and
- coverage adequate for cited paths, or a precisely named coverage gap.

Choose the source group by current claim risk, reusable value, and the quality
of available source/test evidence. Do not use stars, repository size, test
count, or a quota. State the selection reason.

If no source group qualifies, stop with:

```text
STOP: source recovery required
Blocker: <missing pin | source unavailable | license unknown | index stale | coverage gap>
Next route: /inspo <named Foundation claim or source-recovery question>
```

Do not substitute a current checkout head for the recorded pin. Do not call
`/inspo`, clone, or index automatically.

## Chained stop conditions (each group)

Pick the first applicable stop, commit the group record, decide whether the
campaign continues, and update the coordinator:

- `COMPLETE`: every scoped claim has direct evidence or a justified deferral.
- `SATURATED`: no remaining seam can change an in-scope claim.
- `BLOCKED`: a pin/source/license/index gap prevents a sound conclusion;
  record the blocker and the `/inspo` route. Continue to the next eligible
  group only when resolution is not a separate approval gate.
- `CHECKPOINT`: the next pass needs a later session; record verified state
  and next seam, then stop for resume.
- `EDGE`: no eligible group remains (all terminal or blocked); stop and
  summarize the campaign.

A large `--loops` budget never authorizes fabricated coverage, skipped
direct-source verification, or auto-clone/index of unapproved sources. It only
interrupts the between-group pause; every in-group step still runs.

## Long-running coordinator

`/learn --auto` is an explicit request to coordinate the selected source group.
Before its first pass, create or resume one compact
`docs/plans/inspo-learning-<repo>.md` record. It contains the source identity,
pin, license, Foundation claims in scope, named questions, non-goals,
completion and freshness criteria, verified passes, counter-evidence, blockers,
and next target. It is not a source dump or task tracker.

A one-pass manual `/learn` stays in the conversation unless an existing
qualified coordinator owns it.

## Evidence-pass loop

For the selected source group, investigate one high-value Foundation-relevant
concern at a time: entry points, control/data flow, invariants, lifecycle,
configuration, failure/retry/security boundary, or a direct test contract. Use
Codebase Memory to locate and trace; confirm all conclusions in exact source
and test code. Read tests even when they cannot run. Run a test only when it
already works without dependency or environment setup; otherwise report the
unrun-test caveat.

After each pass, report:

```text
Source/pin:
Foundation claims examined:
Verified model:
Exact source/test evidence:
Counter-evidence and coverage caveats:
Disposition: retain | revise | demote | defer
Next candidate seam:
```

Continue only when the next seam can materially strengthen, correct, or
invalidate an in-scope Foundation claim. Stop the source group as one of:

- `COMPLETE`: every scoped claim has direct evidence, a correction, or a
  justified deferral.
- `SATURATED`: remaining paths repeat known facts or cannot change an in-scope
  claim.
- `BLOCKED`: pin, source, test, license, or coverage evidence prevents a sound
  conclusion.
- `CHECKPOINT`: the next pass needs a later session; record verified state and
  the next seam.

Do not use a fixed pass count. "Saturated" means no remaining high-value,
evidence-backed question, not that every repository file was read.

## Revision and capture limits

During a user-approved Foundation Pack revision, make only the smallest
source-backed change to an existing in-scope leaf: correct a stale claim, add
an exact citation, remove unsupported detail, or record `defer`/`demote`.
Run the applicable Foundation validation after a change. Do not create a new
Foundation leaf, a Skill, a generic summary, or a raw memory dump.

At a terminal state, update the coordinator with the verified outcome and next
route. Retain only an expensive-to-reconstruct decision or counter-evidence in
project-scoped memory when the configured memory surface is available. Do not
run generalized synthesis or promote memory automatically.

Request:
$ARGUMENTS
