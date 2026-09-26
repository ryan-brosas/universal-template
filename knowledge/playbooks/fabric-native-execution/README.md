---
title: fabric-native-execution
summary: Use when choosing an optional Pi Fabric execution capability, diagnosing unavailable tools, recovering from stale Fabric guidance, gating a write to a system the user does not control (admin panel, policy list, third-party service) behind a typed decision, or weighing a typed verdict that disagrees with itself across runs; installed host schemas and package skills own the API.
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

- Memory retrieves historical evidence, not current project truth.
- Runtime state and compaction support the session; they do not replace project
  files or require repository-side sync artifacts.
- A child or alternate model can isolate context or supply missing capability.
  A persistent observer needs actual runner support, not just a model name.
  [Prove activation, not transport](references/durable-actors.md) before claiming
  an automatic observer works.
- Transactional mutation modes are deliberate host policy, not prerequisites
  for ordinary edits and not replacements for behavioral tests.
- A write to a system the user does not control (a production admin panel, a
  policy or block list, a third-party service) is an authorization decision
  before it is a data edit. Gate it on a typed decision over the structured
  evidence actually held - what was observed, when, from which source - and
  route low confidence to the human instead of resolving it by intuition. The
  gate earns its cost by flagging the entries whose evidence is thin (in
  practice, near-duplicate names that eyeballing had already mislabelled).
  Collapse the gate to default-apply only when the operator confirms a blanket
  property of a known family; keep it for outliers that could also belong to a
  legitimate population, and state the reversibility of the write. Treat the
  verdict as advisory evidence, not ground truth: the same evidence can score
  confidently in one run and barely above chance in another, so a verdict that
  contradicts an earlier run on unchanged input is itself a low-confidence signal.
  Prefer the structure of the evidence - how many independent sources, whether one
  shape or naming template spans them, how they cluster in time - and escalate when
  structure and verdict disagree rather than letting either decide alone.

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
A handoff digest can likewise arrive in place of a read result for calls that did
complete; re-issue the harmless read rather than inferring failure from the missing
return. This does not authorize replaying mutations without checking their effects.

A newly configured server can register while reporting no tools until first use;
prove the connection and its credential with one read-only call that requires
the credential, not with a registration listing. A surface that declines
credential entry on a login, 2FA or consent step is enforcing a boundary rather
than failing: complete that step by hand and resume automation on the
authenticated session (`../security-and-hardening/README.md`).
A long-lived process serves the tool surface it loaded at startup, so a server
added to the host config afterwards looks absent and a removed server looks
present until that configuration is reloaded (`mcp.$reload` in Fabric).
Observed 2026-09-11: `github` gained 47 tools and `deepwiki`/`openviking`
vanished after one reload. An absent entry is not evidence that a server is
unavailable; reload and re-list before concluding anything from it.

Identify which file the consumer of a surface reads before editing one or
restarting to pick a server up. Several config files can carry the same servers
for different consumers and different schemas; an edit to the wrong one survives
any number of restarts as a still-absent server. Resolve the indirection first,
since a host config can name the path the runtime actually loads. Observed
2026-09-27: two files listed most of the same servers, the runtime read only the
one named by its own `configPath`, and a correct-looking entry in the other file
never appeared no matter how many times the host restarted.

A config that loads can still contribute nothing. An entry missing a field its
working siblings all carry is dropped with no error and no warning, so compare
the entry against one known to work rather than the schema you remember. Treat
"no error, no server" as a validation problem before a connectivity problem.

Prefer reload over restart, and expect reload to be slow and lossy: it
reconnects every server, the first attempt here exceeded 60 s, and it discards
live session state held by servers such as a REPL. When a runtime registration or
dynamic call route hangs instead of failing, treat it as unsupported in that host
and use the supported reload path; a hang is not evidence that the server is
broken.

Inspect credential-bearing configuration by allowlisted field or presence
boolean, never by dumping entry shapes: a shape comparison still prints a bare
token field, and later redaction does not undo transcript exposure
(`../security-and-hardening/README.md`).
A model naming a file proves neither that it read the file nor that it followed
its instructions. Report prompt inclusion, tool execution, and behavioral
compliance separately; stop when the requested claim has sufficient evidence.

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
