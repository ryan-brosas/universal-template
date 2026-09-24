---
title: fabric-native-execution
summary: Use when choosing an optional Pi Fabric execution capability, diagnosing unavailable, skipped or restricted tools, inspecting or removing durable actors, recovering from a prewalk handoff boundary, or recovering from stale Fabric guidance; installed host schemas and package skills own the API.
kind: playbook
---

# Fabric execution context

Use the active host's core tools for ordinary work. In Fabric full-code mode
those are exposed through `fabric_exec`; follow its supplied guidance rather
than this template's remembered API signatures.

For unfamiliar mechanics, discover the installed Fabric skill or current tool
schema. The package's `fabric-exec` reference owns call shapes, provider methods,
runner support and error recovery. This template deliberately does not mirror
that live documentation. If a capability is absent, use available tools or
report the specific blocker, not an invented substitute result.

Optional capabilities have different jobs:

- Memory retrieves historical evidence, not current project truth. For missing
  tool attachments or build-source payloads, use
  [artifact recovery](references/artifact-recovery.md) before asking for a resend.
- Runtime state and compaction support the session; they do not replace project
  files or require repository-side sync artifacts.
- A child or alternate model can isolate context or supply missing capability.
  A persistent observer needs actual runner support, not just a model name.
  Inspect live actors before attaching a capability. If removal is requested,
  follow [durable actors](references/durable-actors.md); a restricted allowlist
  does not itself authorize retiring the actor.
- Jev supplies bounded typed judgments, not generated reasoning or proof. Use
  [typed judgment workflows](../typed-judgment-workflows/README.md) for task fit
  and portability; installed Jev documentation and live schemas own execution.
- Transactional mutation modes are deliberate host policy, not prerequisites
  for ordinary edits and not replacements for behavioral tests.

## Diagnose tool availability before repeating probes

Distinguish tools exposed to the model from operations behind an executor. A
CLI allowlist of underlying operation names may exclude the executor that makes
those operations callable. Inspect the active tool surface and installed host
policy before changing flags; do not infer a mode-wide limitation from a model
saying it has no tools.

After a failed probe, change one evidence-backed assumption before retrying.
Use a harmless read through the actual exposed route and inspect its tool result.
An unreachable server can hang until the program deadline instead of failing fast,
and the harness then discards sibling results that had already completed. Observed
2026-09-17: a down Sourcebot endpoint exceeded the 120 s `fabric_exec` deadline and an
already-finished `pi.bash` read was lost, so the same reads had to be repeated. Run
local reads first and return them before probing a suspect remote endpoint, and give
that probe its own bounded program; a settled rejection carrying an empty reason is
likewise not evidence of the cause, so probe the transport directly.
A newly configured server can register while reporting no tools until first use;
prove the connection and its credential with one read-only call that requires
the credential, not with a registration listing.
A long-lived process serves the tool surface it loaded at startup, so a server
added to the host config afterwards looks absent and a removed server looks
present until that configuration is reloaded (`mcp.$reload` in Fabric).
Observed 2026-09-11: `github` gained 47 tools and `deepwiki`/`openviking`
vanished after one reload. An absent entry is not evidence that a server is
unavailable; reload and re-list before concluding anything from it.
A model naming a file proves neither that it read the file nor that it followed
its instructions. Report prompt inclusion, tool execution, and behavioral
compliance separately; stop when the requested claim has sufficient evidence.

When a capability is configured but skipped, or its live description restricts
the workflow that recommends it, trace the conflict to its owner instead of
adding another rule: [tool adoption](references/tool-adoption.md).

Before building a replacement client, transport or adapter to exercise a
capability, make one bounded attempt through the supported native path and inspect
its receipt. Once that plumbing works, attempt the first independently gradable
task before expanding runner infrastructure. A failed task still supplies evidence;
a successful transport canary does not complete the task. Observed 2026-09-21:
benchmark work remained in adapter setup while the native CLI could already run
the intended model pairing.

If blocked, identify the missing control that justifies a different harness. A
cheaper or single-model substitute changes the experiment: obtain authorization
for that change rather than counting it toward the original comparison. Building
a runner can itself be the deliverable, and native execution may genuinely lack
a required control. Neither route permits exceeding the authorized spend or
safety limits; report the blocked task and the evidence each route could supply.

Verify any load-bearing delegated claim against current source and tests.

## Escape patterns for the shell deliberately

Account for the TypeScript string, shell quoting and regex dialect separately.
In a TypeScript string, `"alpha\|beta"` loses the backslash and becomes `alpha|beta`.
Quoted as the pattern for basic `grep`, that matches a literal pipe; it is not
alternation. `"alpha\\|beta"` preserves the backslash for GNU basic `grep`.
Extended regex (`grep -E`) and `pi.grep` instead use plain `alpha|beta` for
alternation. Prefer `pi.grep` to avoid the shell layer, and `literal: true` when
searching exact text. Verify surprising empty results before claiming absence.

## After a rejected program

`Type errors; code was not executed` means no call in that program ran, including
mutations before the bad line. Correct the type error before retrying; do not
report the planned effect as applied. A runtime failure can instead leave earlier
calls applied: inspect affected files and returned results before resuming, and
retry only unfinished work. Never compensate for a mutation merely assumed to
have happened.

For paid or otherwise consequential calls, save the safe response in the existing
task receipt before parsing, assertions or follow-up calls can fail. Exclude
credentials and temporary signed URLs. Prefer structured content; otherwise inspect
text blocks independently against the expected schema. A response may mix JSON with
prose, including billing units or warnings: do not parse every block as JSON or
silently discard the non-JSON context. Preserve operation IDs and reported units;
an estimate is not a charge. If parsing fails, recover from the receipt and inspect
the operation by ID or affected resource before considering a retry. A successful
operation record alone may not retain its returned payload.

## Recover from a prewalk handoff boundary

The installed package owns prewalk modes, trigger detection and configuration.
Current in-place prewalk lets the full outer Fabric invocation settle before
switching Main and queuing its continuation. A handoff summary is not evidence
that the nested calls were interrupted or rolled back.

- Re-anchor on the latest actual user request before following a recorded plan.
  A continuation does not authorize extra deliverables or write targets: research
  and indexing can authorize an index update without permitting application edits.
  Treat earlier implementation plans as context after a task change. If
  implementation is explicitly requested, continue within that scope without
  seeking redundant permission.
- Do not replay a mutation batch merely because its normal return value is absent.
  Read the affected files, recover recorded results when available, and continue
  only the unfinished work. A handoff digest can likewise arrive in place of a read
  result for calls that did complete, so re-issue the harmless read rather than
  inferring a failure from the missing return.
- For an unexpected boundary, inspect the reported trigger, active configuration
  and installed package documentation. Filesystem-drift detection is version- and
  scope-dependent; a bookkeeping path alone does not establish a trigger bug.
- Distinguish the session arm from the persistent master switch. Do not change
  either configuration simply to suppress an unexplained result.
- Keep an expected nonzero probe behind `settle:true` or a per-call `try/catch`,
  so one failure cannot hide successful sibling results.
- A restored model selection is not a completed review. Returning ownership to
  Main proves which model is selected. If independent verification is expected,
  require its own evidence - a request, a check result, an explicit decision -
  rather than inferring review from the switch.
