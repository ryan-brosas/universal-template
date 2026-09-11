---
name: semantic-kernel-foundation
description: Use when porting Semantic Kernel's Python kernel-core machinery — filter call-stack onion, corrective tool-call feedback, bounded auto-invoke loop, exception smuggling, OTel-gated telemetry, decorator-time metadata, argument coercion, copy-on-add plugin registries, the {{...}} prompt-template block engine, HTML trust gates, AI service selection/registration, tool-view generation, prompt-config parsing ladders, Jinja2/Handlebars helper-binding/sandbox, streaming auto-invoke twin, .NET method-function/filter mirrors, and the agents plane (Assistant run lifecycle, requires-action handoff, Responses auto-invoke loop, agent merge twins, function-choice gate, Azure AI run lifecycle + approval gate, Azure streaming event plane, request-prep flattening, handoff turn-taking, .NET FunctionChoiceBehavior twin, the AutoGen-style actor runtime (envelope queue, intervention gate, routed handlers, subscriptions, serialization registry, telemetry links), Responses streaming item mapping, and the AgentChannel protocol).
kind: foundation
invocation: manual
disable-model-invocation: true
---
# Semantic Kernel: kernel-core invocation foundation

## Foundation contract

This is a cold, source-specific foundation, not an operational procedure. It is
historical, revision-pinned evidence rather than timeless guidance. Current
project source, tests, requirements, and runtime behavior outrank this
projection and decide what ships.

## Provenance and revision

- Source record: `semantic-kernel`; portable upstream identity, license, coverage caveats, and retrieval history are preserved in the index.
- Recorded revision: `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`.
- Full provenance, coverage caveats, boundaries, and preserved evidence:
  `references/index.md`.

## Topic map

- Representative topics: Filter onion; Corrective feedback; Bounded auto-
  invoke; Error absorption; Stream smuggling; Telemetry wrapper; Decorator
  contract; Type parsing ladder.
- Scope and retrieval questions: `references/index.md#use-this-for`.
- Complete capsule chooser: `references/index.md#load-the-matching-source-dump`.
- Detailed grouped map: `references/index.md#capsule-map`.
- Source limitations and portability boundaries: `references/index.md#boundaries`.

## Retrieval

Open the index, choose one capsule matching the active question, and load only
that capsule. Revalidate its cited source and revision before relying on it. Do
not bulk-load the inventory, treat historical claims as current truth, or apply
this foundation as a procedure.
