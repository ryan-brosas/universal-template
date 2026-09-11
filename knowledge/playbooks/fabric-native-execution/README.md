---
title: fabric-native-execution
summary: Use when choosing an optional Pi Fabric execution capability, diagnosing unavailable tools, or recovering from stale Fabric guidance; installed host schemas and package skills own the API.
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
A model naming a file proves neither that it read the file nor that it followed
its instructions. Report prompt inclusion, tool execution, and behavioral
compliance separately; stop when the requested claim has sufficient evidence.

Use `../execution-router/README.md` or `../model-resolution/README.md` only when
the execution shape or model choice is a genuine open question. Verify any
load-bearing delegated claim against current source and tests.
