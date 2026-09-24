---
title: autonomous-agent-teams
summary: "Use when an agent coordinator does the specialist's work, a handoff does not wake a teammate, or an autonomous team needs bounded orchestration, per-agent judgment, task learning, or workspace separation. Distinguishes configured capabilities from observed behavior."
kind: playbook
---

# Make agent teams operational

Role prompts describe a team; dispatch, authority, persistence, and observable
outcomes make it operational. Start with one bounded workflow, not more bots or
an always-on supervisor.

## Establish the live contract

Trace the running revision, execution mode, available delivery tools, trigger
restrictions, room capacity, reply routing, and skill discovery in the actual
recipient runtime. See [runtime provenance](../runtime-artifact-provenance/README.md)
when tested source and deployed behavior differ. Do not instruct staff to use a
staged feature or infer child capabilities from the coordinator's session.

Inspect how mentions are parsed: assistant prose may wake nobody, while several
mentions in a user message may start several runs. An unaddressed reply may reach
a default member rather than the last speaker. Scope approvals to the actor,
action, resource, and task; a bare "yes" is not transferable authorization.

## Prove one complete handoff

- Assign a coordinator, the needed specialist, and an independent verifier.
  Check room limits before expanding membership; share policy rather than copying
  it into divergent role prompts.
- Give each handoff the goal, evidence, acceptance checks, authorized scope,
  prohibited effects, and expected next owner. Use the runtime's dispatch tool;
  inspect its receipt and recipient run, not an announcement of delegation.
- Determine whether handoff transfers ownership or returns a result. Do not
  promise automatic resumption unless the runtime implements it. Bound hops and
  revisions; avoid immediate bounce-backs and acknowledgement loops.
- If delegation is refused, report the precise blocker. Continue unaffected,
  authorized work, but do not bypass the boundary or silently take over the
  specialist's assignment. Enforce coordinator-only access through capabilities
  when required; prompts alone cannot guarantee it.

Probe with synthetic inputs, one explicit starting recipient, and external
effects disabled at the execution boundary. Observe distinct specialist and
verifier runs, terminal results, and actual effects. A successful dispatch is not
proof of completion or of continuously running autonomy.

## Put judgment inside a bounded controller

Use [typed judgment workflows](../typed-judgment-workflows/README.md) for Jev
routing or review triage. The controller owns execution; the judge does not grant
permission, certify correctness, or override a required escalation. Keep explicit
no-match and unavailable-backend outcomes. Tool access does not authorize sending
messages across every accessible community or account.

For restart-durable work, persist stage state and evidence; bound attempts, time,
and spend. Test duplicate wakes, concurrent claims, stale writers, cancellation,
and scope revocation. Idempotent commits do not make inference billing exactly
once. Verify dispatch registration and recovery in every process that runs jobs.

A text-only stage requires a verified tool-less provider path. Do not substitute
a tool-capable native agent merely because its model works interactively. Session
observers are not durable workers; reuse existing queues before adding another.

## Learn without accumulating noise

Review evidence after each task; retain only reusable corrections or methods.
Use the [session improvement compiler](../session-improvement-compiler/README.md),
updating an existing owner first. "No reusable lesson" is valid. Read-only roles
propose changes to the writer; learning does not expand permissions or authorize
shared-library edits. Put a short disposition in the normal result, not a new
recursive learning task. This updates instructions, not model weights.

## Verification and related work

Report configured, tested, deployed, and behaviorally observed states separately.
Synthetic judgment probes establish usability, not routing quality. Confirm the
composed policy reaches each profile without overwriting unrelated settings.

- Proving ordinary bots use Jev, and checking efficiency claims:
  [per-agent judgment](references/per-agent-judgment.md).
- Moving staff into a company space: [workspace moves](references/workspace-moves.md).
- Checking a proposed design: [acceptance cases](references/acceptance-cases.md).
