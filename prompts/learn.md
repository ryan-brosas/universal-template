# Learn an approved source

Use this command to investigate source and tests, not to manufacture knowledge.
Codebase Memory is a structural map. Direct source and direct tests decide what
is true. Keep findings compact, cited, and useful for the active project.

## Modes

- `/learn <source or question>`: run one manual evidence pass on an already
  approved source.
- `/learn --auto foundation-pack`: run one bounded revision campaign over ONE
  eligible Foundation Pack source group at a time; after the first group
  reaches its group disposition, end the run.
- `/learn --auto foundation-pack --loop [N]` (alias `--loops N`): run a
  continuous, sequential campaign. Omit N, or pass the words "continuous"/"run
  until done" when the host mangles flags, to run until a run-level stop; pass
  a positive integer N to cap the campaign at N source groups. Do not stop
  between groups: after a group reaches a terminal state, select the next
  eligible group and continue.
- `/learn --auto foundation-pack continue`: resume a campaign that stopped at
  a run-level stop. Read the coordinator deterministically: consider
  `docs/plans/inspo-learning-*.md` in ascending `(repo pin)` order and take
  the first record whose group has no COMPLETE or SATURATED terminal
  disposition recorded. A record that already records COMPLETE or SATURATED for
  its pinned seams is closed: do not re-enter or re-approve it. Use that
  record's `Next target` first, finish that seam, then chain on to the next
  eligible source group.
- `/learn --auto foundation-pack --reflect`: after the run, invoke the
  read-only `/reflect-memory` pass over project memory before recommending a
  new campaign batch.

`--auto` without a `foundation-pack` target is a usage error: state the target
explicitly and stop.

## Run and group contract

A campaign has two units of execution. A **group** is one source group reached
through the eligibility check below; it terminates with exactly one
*group disposition*: COMPLETE, SATURATED, BLOCKED, or CHECKPOINT. A run is
the sequence of groups a single `/learn --auto foundation-pack` invocation
processes. In a `--loop` run the group dispositions never end the run:

- COMPLETE: every scoped claim has direct evidence or a justified deferral.
  Record it, then advance.
- SATURATED: no remaining seam can change an in-scope claim. Record it,
  advance.
- BLOCKED: a pin/source/license/index gap prevents a sound conclusion. Record
  the blocker and the `/inspo` route in that group's record, then advance
  to the next eligible group. It ends the run only when the next eligible
  group is itself blocked by that recovery or approval action.
- CHECKPOINT: a later session is needed to close a seam. Record verified
  state and the next seam, then end the run: `continue` resumes exactly
  there. Never advance past a checkpoint in the same run.
- EDGE: no eligible group remains. End the run and summarize the campaign.

The run as a whole ends only at a run-level stop, which is exactly ONE of:

- the group budget N was reached (a `--loop N` cap);
- EDGE;
- an approval gate bound to the next eligible group (`/inspo` review, index
  restore, or cloning a candidate);
- the explicit user interruption ("stop");
- CHECKPOINT that requires a later session (above).

Report after each group, even in mid-run: budget used, groups terminal,
groups blocked, next seam, and what a fresh `continue` resumes. A `--loop`
run does not pause and wait for a user decision after each report; that
report is for the user's visibility only. If the host mangles the flags, the
words "run continuously" or "keep going until no group remains" mean the
same as `--loop`.

`--auto` authorizes in-session selection and repeat of evidence passes. It
does not authorize unattended work, GitHub discovery, cloning, indexing,
dependency installation, setup scripts, bulk mining, or promotion into a new
foundation or Skill. A blocked group records its missing-source route in
its own record; that does not end the run. A run stops only when the next
eligible group is itself blocked by that approval or recovery action. A
one-shot `/learn` does route and stop. A very
large or even unbounded `--loop` never authorizes fabricated coverage,
skipped direct-source verification, or auto-clone/index of unapproved
sources. It only relaxes the between-group count limit; the in-group steps
are never skipped or weakened.

## Preflight

Read the current project's instructions, relevant Foundation Pack leaves, their
portable source identity and exact pin, and the existing migration/work record.
For `--auto foundation-pack`, group leaves by upstream identity and exact pin.
Choose one source group only when it has:

- a Foundation Pack claim with a named evidence gap;
- readable source at the recorded exact pin;
- a recorded license or explicit `NO-LICENSE` limitation;
- a ready full-mode Codebase Memory index; and
- coverage adequate for cited paths: a named coverage gap is fine when
  recorded.

Choose a group by current claim risk, reusable value, and quality of available
source/test evidence, not by stars, repository size, test count, or quota.
State the selection reason. If no source group qualifies, stop with:

```text
STOP: source recovery required
Blocker: <missing pin | source unavailable | license unknown | index stale | coverage gap>
Next route: /inspo <named Foundation claim or source-recovery question>
```

Do not substitute a current checkout head for the recorded pin. Do not call
`/inspo`, clone, or index automatically.

## Long-running coordinator

`/learn --auto` is an explicit request to coordinate a selected source group.
Before its first pass, create or resume one compact
`docs/plans/inspo-learning-<repo>.md` record: identity, pin, license,
Foundation claims in scope, named questions, non-goals, completion and
freshness criteria, verified passes, counter-evidence and blockers, and next
target. It is not a source dump or task list. A one-pass manual `/learn`
stays in the conversation unless an existing qualified coordinator owns it.

## Evidence-pass loop

For a selected source group, investigate one high-value Foundation-relevant
concern: entry points, control/data flow, invariants, lifecycle,
configuration, failure/retry/security boundary, or a test contract. Use
Codebase Memory to locate and trace; confirm all conclusions in exact source
and test code. Read tests even when they cannot run; run a test only when it
works without dependency/environment setup, otherwise record the unrun-test
caveat.

Report after each pass:

```text
Source / pin:
Foundation claims examined:
Verified model:
Exact source/test evidence:
Counter-evidence and coverage caveats:
Disposition: retain | revise | demote | defer
Next seam:
```

Continue only when the next seam can materially change a claim in scope.
Stop the source group at one of: COMPLETE (all claims have direct evidence or
a justified deferral), SATURATED (remaining paths repeat known facts),
BLOCKED (a pin/source/test/license/coverage gap prevents a sound conclusion),
or CHECKPOINT (a later session is needed; record state and the next seam).
Do not use a fixed pass count. SATURATED is not about file breadth.

## Revision and capture limits

During a user-approved Foundation Pack revision, make only the smallest
source-backed change to an existing in-scope leaf: correct a stale claim, add
an exact citation, remove unsupported detail, or record `defer`/`demote`.
Run the approval validation after each change. Do not create a new Foundation
leaf, Skill, summary, or raw dump.

At a terminal state, update the coordinator with the verified outcome and next
route. Retain only the expensive-to-reconstruct decisions or
counter-evidence in project-scoped memory when available. Do not run
synthesis or promote memory automatically.

Request:
$ARGUMENTS
